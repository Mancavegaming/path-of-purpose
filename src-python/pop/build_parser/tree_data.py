"""Passive tree URL generator.

Fetches PoE passive tree data from pathofexile.com, resolves node names to IDs,
pathfinds from class start to target notables, and encodes pathofexile.com URLs.
"""

from __future__ import annotations

import base64
import json
import logging
import math
import struct
from collections import deque
from pathlib import Path

import httpx
from rapidfuzz import fuzz, process

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent.parent / "knowledge" / "cache"
TREE_CACHE = CACHE_DIR / "passive_tree.json"
LAYOUT_CACHE = CACHE_DIR / "passive_tree_layout.json"

# Serialization version 6 = modern PoE 1 tree URL format
TREE_SERIAL_VERSION = 6

# Class name → class_id (matches PoE's encoding)
CLASS_IDS: dict[str, int] = {
    "scion": 0,
    "marauder": 1,
    "ranger": 2,
    "witch": 3,
    "duelist": 4,
    "templar": 5,
    "shadow": 6,
}


class TreeData:
    """Parsed passive skill tree with lookup and pathfinding."""

    def __init__(self, raw: dict, version: str = "3.28.0"):
        self.version = version
        self.nodes: dict[int, dict] = {}
        self.adjacency: dict[int, set[int]] = {}
        self.class_starts: dict[int, int] = {}  # class_id → skill_id
        self.name_to_ids: dict[str, list[int]] = {}  # lowercase name → skill_ids
        self.ascendancy_map: dict[str, tuple[int, int]] = {}  # lowercase asc → (class_id, asc_id)
        self._parse(raw)

    def _parse(self, raw: dict) -> None:
        raw_nodes = raw.get("nodes", {})

        # Build ascendancy map from class data
        for class_data in raw.get("classes", []):
            class_name = class_data.get("name", "")
            class_id = CLASS_IDS.get(class_name.lower())
            if class_id is None:
                continue
            for i, asc in enumerate(class_data.get("ascendancies", []), start=1):
                asc_name = asc.get("name", "")
                if asc_name:
                    self.ascendancy_map[asc_name.lower()] = (class_id, i)

        # First pass: index all nodes
        for nid_str, node in raw_nodes.items():
            if nid_str == "root":
                continue
            skill_id = node.get("skill")
            if skill_id is None:
                try:
                    skill_id = int(nid_str)
                except ValueError:
                    continue
            self.nodes[skill_id] = node

            # Name lookup for notables/keystones (skip bloodline alternate ascendancy nodes)
            name = node.get("name", "").strip()
            if name and (node.get("isNotable") or node.get("isKeystone")):
                if not node.get("isBloodline"):
                    self.name_to_ids.setdefault(name.lower(), []).append(skill_id)

            # Class start nodes
            csi = node.get("classStartIndex")
            if csi is not None:
                self.class_starts[csi] = skill_id

        # Second pass: build bidirectional adjacency from 'out' connections
        for nid_str, node in raw_nodes.items():
            if nid_str == "root":
                continue
            skill_id = node.get("skill")
            if skill_id is None:
                try:
                    skill_id = int(nid_str)
                except ValueError:
                    continue

            for out_str in node.get("out", []):
                out_node = raw_nodes.get(out_str)
                if out_node is None:
                    continue
                out_skill = out_node.get("skill")
                if out_skill is None:
                    try:
                        out_skill = int(out_str)
                    except ValueError:
                        continue
                self.adjacency.setdefault(skill_id, set()).add(out_skill)
                self.adjacency.setdefault(out_skill, set()).add(skill_id)

    def resolve_name(self, name: str) -> int | None:
        """Resolve a notable/keystone name to its skill_id. Falls back to fuzzy match."""
        lower = name.strip().lower()
        if lower in self.name_to_ids:
            # Prefer non-ascendancy node
            for nid in self.name_to_ids[lower]:
                if not self.nodes[nid].get("ascendancyName"):
                    return nid
            return self.name_to_ids[lower][0]

        # Fuzzy match against all notable/keystone names
        all_names = list(self.name_to_ids.keys())
        if not all_names:
            return None
        result = process.extractOne(lower, all_names, scorer=fuzz.ratio, score_cutoff=75)
        if result:
            matched = result[0]
            for nid in self.name_to_ids[matched]:
                if not self.nodes[nid].get("ascendancyName"):
                    return nid
            return self.name_to_ids[matched][0]
        return None

    def get_class_info(self, class_name: str, ascendancy_name: str) -> tuple[int, int, int | None]:
        """Return (class_id, ascendancy_id, start_node_id) for the given class/ascendancy."""
        asc_lower = ascendancy_name.strip().lower()
        if asc_lower in self.ascendancy_map:
            class_id, asc_id = self.ascendancy_map[asc_lower]
        else:
            class_id = CLASS_IDS.get(class_name.strip().lower(), 0)
            asc_id = 0
        start_node = self.class_starts.get(class_id)
        return class_id, asc_id, start_node

    def pathfind(self, start: int, targets: list[int], allocated: set[int] | None = None) -> set[int]:
        """BFS from allocated nodes to each target. Returns the full allocation set."""
        if allocated is None:
            allocated = {start}
        else:
            allocated = set(allocated)
            allocated.add(start)

        for target in targets:
            if target in allocated:
                continue
            path = self._bfs(allocated, target)
            if path:
                allocated.update(path)

        return allocated

    def _bfs(self, sources: set[int], target: int) -> list[int] | None:
        """BFS from any source to target. Returns path nodes (excluding sources)."""
        queue: deque[int] = deque()
        parent: dict[int, int | None] = {}

        for s in sources:
            queue.append(s)
            parent[s] = None

        while queue:
            current = queue.popleft()
            if current == target:
                path = []
                node = current
                while node is not None and node not in sources:
                    path.append(node)
                    node = parent[node]
                return path

            for neighbor in self.adjacency.get(current, set()):
                if neighbor in parent:
                    continue
                # Skip ascendancy nodes unless they're the target
                nd = self.nodes.get(neighbor, {})
                if nd.get("ascendancyName") and neighbor != target:
                    continue
                # Skip class start nodes for other classes
                if nd.get("classStartIndex") is not None and neighbor not in sources:
                    continue
                parent[neighbor] = current
                queue.append(neighbor)

        return None


def encode_tree_url(
    version: str,
    class_id: int,
    ascendancy_id: int,
    node_ids: set[int],
) -> str:
    """Encode allocated node IDs into a pathofexile.com passive tree URL."""
    header = struct.pack(">IBBB", TREE_SERIAL_VERSION, class_id, ascendancy_id, 0)
    body = b"".join(struct.pack(">H", nid) for nid in sorted(node_ids) if 0 < nid <= 65535)
    payload = header + body
    encoded = base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")

    # Normalize version: ensure X.Y.Z format
    vs = version.replace("_", ".")
    if vs.count(".") < 2:
        vs += ".0"

    return f"https://www.pathofexile.com/passive-skill-tree/{vs}/{encoded}"


async def fetch_tree_data(version: str = "3.28.0") -> TreeData:
    """Fetch passive tree data from pathofexile.com, caching locally."""
    if TREE_CACHE.exists():
        try:
            raw = json.loads(TREE_CACHE.read_text(encoding="utf-8"))
            cached_version = raw.get("_version", "")
            if cached_version == version:
                return TreeData(raw, version)
        except Exception:
            logger.warning("Failed to load cached tree data, re-fetching")

    url = f"https://www.pathofexile.com/passive-skill-tree/{version}/"
    async with httpx.AsyncClient(
        headers={"User-Agent": "PathOfPurpose/1.0 (build advisor)"},
        timeout=30,
        follow_redirects=True,
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        html = resp.text

    # Extract JSON from 'var passiveSkillTreeData = {...}'
    marker = "var passiveSkillTreeData = {"
    start_idx = html.find(marker)
    if start_idx < 0:
        raise ValueError("Could not find passiveSkillTreeData in page")

    brace_start = html.index("{", start_idx)
    depth = 0
    end_idx = brace_start
    for i in range(brace_start, len(html)):
        if html[i] == "{":
            depth += 1
        elif html[i] == "}":
            depth -= 1
        if depth == 0:
            end_idx = i + 1
            break

    raw = json.loads(html[brace_start:end_idx])

    # Cache without bulky image data
    cache_data = {
        k: v for k, v in raw.items()
        if k not in ("sprites", "imageZoomLevels", "extraImages")
    }
    cache_data["_version"] = version
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    TREE_CACHE.write_text(json.dumps(cache_data, separators=(",", ":")), encoding="utf-8")
    logger.info("Cached passive tree data (%d nodes) for %s", len(raw.get("nodes", {})), version)

    return TreeData(raw, version)


async def resolve_guide_tree_urls(guide: dict, version: str = "3.28.0") -> dict:
    """Post-process a BuildGuide dict: resolve key_nodes → tree URLs for each bracket.

    Progressive allocation: each bracket builds on the previous one's nodes.
    """
    tree = await fetch_tree_data(version)

    class_name = guide.get("class_name", "")
    ascendancy_name = guide.get("ascendancy_name", "")
    class_id, asc_id, start_node = tree.get_class_info(class_name, ascendancy_name)

    if start_node is None:
        logger.warning("No start node for class %s (id=%d)", class_name, class_id)
        return guide

    allocated: set[int] = set()

    for bracket in guide.get("brackets", []):
        pt = bracket.get("passive_tree")
        if not pt or not pt.get("key_nodes"):
            continue

        # Resolve notable names → skill IDs
        target_ids = []
        for name in pt["key_nodes"]:
            nid = tree.resolve_name(name)
            if nid is not None:
                target_ids.append(nid)
            else:
                logger.debug("Could not resolve node: %s", name)

        if not target_ids:
            continue

        # Progressive pathfinding — each bracket extends the previous allocation
        allocated = tree.pathfind(start_node, target_ids, allocated)

        # Generate the tree URL
        pt["url"] = encode_tree_url(tree.version, class_id, asc_id, allocated)

    return guide


# Non-uniform orbit angles (degrees) used by PoE passive tree renderer.
# Orbits with 16 and 40 nodes use specific angle sets, not uniform spacing.
_ORBIT_ANGLES_16 = [0, 30, 45, 60, 90, 120, 135, 150, 180, 210, 225, 240, 270, 300, 315, 330]
_ORBIT_ANGLES_40 = [
    0, 10, 20, 30, 40, 45, 50, 60, 70, 80, 90, 100, 110, 120, 130, 135, 140,
    150, 160, 170, 180, 190, 200, 210, 220, 225, 230, 240, 250, 260, 270, 280,
    290, 300, 310, 315, 320, 330, 340, 350,
]


def _orbit_angle_rad(orbit_index: int, skills_in_orbit: int) -> float:
    """Get the angle in radians for a node at a specific orbit position."""
    if skills_in_orbit == 16:
        return math.radians(_ORBIT_ANGLES_16[orbit_index % 16])
    elif skills_in_orbit == 40:
        return math.radians(_ORBIT_ANGLES_40[orbit_index % 40])
    else:
        return 2 * math.pi * orbit_index / skills_in_orbit


async def compute_tree_layout(version: str = "3.28.0") -> dict:
    """Compute x,y positions for all tree nodes. Returns compact layout data.

    Layout format:
      nodes: [[skill_id, x, y, type_code, "name"], ...]
      edges: [[from_id, to_id], ...]
      bounds: [min_x, min_y, max_x, max_y]

    type_code: 0=normal, 1=notable, 2=keystone, 3=mastery, 4=jewel, 5=start
    """
    # Check for cached layout
    if LAYOUT_CACHE.exists():
        try:
            cached = json.loads(LAYOUT_CACHE.read_text(encoding="utf-8"))
            if cached.get("version") == version:
                return cached
        except Exception:
            pass

    # Load raw tree data
    if not TREE_CACHE.exists():
        await fetch_tree_data(version)
    raw = json.loads(TREE_CACHE.read_text(encoding="utf-8"))

    constants = raw.get("constants", {})
    orbit_radii = constants.get("orbitRadii", [0, 82, 162, 335, 493, 662, 846])
    skills_per_orbit = constants.get("skillsPerOrbit", [1, 6, 16, 16, 40, 72, 72])
    groups = raw.get("groups", {})
    raw_nodes = raw.get("nodes", {})

    layout_nodes = []
    edges_set: set[tuple[int, int]] = set()
    valid_ids: set[int] = set()

    for nid_str, node in raw_nodes.items():
        if nid_str == "root":
            continue

        skill_id = node.get("skill")
        if skill_id is None:
            try:
                skill_id = int(nid_str)
            except ValueError:
                continue

        # Skip bloodline (alternate ascendancy) nodes
        if node.get("isBloodline"):
            continue

        group_id = str(node.get("group", ""))
        group = groups.get(group_id)
        if not group:
            continue

        orbit = node.get("orbit", 0)
        orbit_index = node.get("orbitIndex", 0)

        if orbit >= len(orbit_radii):
            continue

        radius = orbit_radii[orbit]
        n_in_orbit = skills_per_orbit[orbit] if orbit < len(skills_per_orbit) else 1
        angle = _orbit_angle_rad(orbit_index, n_in_orbit)

        x = group["x"] + radius * math.sin(angle)
        y = group["y"] - radius * math.cos(angle)

        # Determine node type
        if node.get("classStartIndex") is not None:
            ntype = 5
        elif node.get("isKeystone"):
            ntype = 2
        elif node.get("isNotable"):
            ntype = 1
        elif node.get("isMastery"):
            ntype = 3
        elif node.get("isJewelSocket"):
            ntype = 4
        else:
            ntype = 0

        name = node.get("name", "")
        asc_name = node.get("ascendancyName", "")

        layout_nodes.append([skill_id, round(x, 1), round(y, 1), ntype, name, asc_name])
        valid_ids.add(skill_id)

    # Collect unique undirected edges (only between valid/rendered nodes)
    for nid_str, node in raw_nodes.items():
        if nid_str == "root":
            continue
        skill_id = node.get("skill")
        if skill_id is None:
            try:
                skill_id = int(nid_str)
            except ValueError:
                continue
        if skill_id not in valid_ids:
            continue

        for out_str in node.get("out", []):
            out_node = raw_nodes.get(out_str)
            if out_node is None:
                continue
            out_skill = out_node.get("skill")
            if out_skill is None:
                try:
                    out_skill = int(out_str)
                except ValueError:
                    continue
            if out_skill not in valid_ids:
                continue
            edge = (min(skill_id, out_skill), max(skill_id, out_skill))
            edges_set.add(edge)

    edges = [list(e) for e in edges_set]

    bounds = [
        raw.get("min_x", -14000),
        raw.get("min_y", -11000),
        raw.get("max_x", 13000),
        raw.get("max_y", 11000),
    ]

    layout = {
        "nodes": layout_nodes,
        "edges": edges,
        "bounds": bounds,
        "version": version,
    }

    # Cache the layout
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    LAYOUT_CACHE.write_text(json.dumps(layout, separators=(",", ":")), encoding="utf-8")
    logger.info("Cached tree layout: %d nodes, %d edges", len(layout_nodes), len(edges))

    return layout
