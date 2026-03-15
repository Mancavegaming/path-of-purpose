"""
Passive tree node stat extraction for the damage calculator.

Resolves a set of allocated node IDs to their stat grants by reading
the cached passive tree JSON and parsing each node's stats text through
the mod_parser.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pop.calc.mod_parser import ParsedMods, parse_mods

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent.parent / "knowledge" / "cache"
TREE_CACHE = CACHE_DIR / "passive_tree.json"


def _load_tree_nodes() -> dict[int, dict]:
    """Load passive tree nodes from the local cache.

    Returns:
        Dict mapping skill_id -> node dict.
    """
    if not TREE_CACHE.exists():
        logger.warning("No passive tree cache at %s", TREE_CACHE)
        return {}

    raw = json.loads(TREE_CACHE.read_text(encoding="utf-8"))
    raw_nodes = raw.get("nodes", {})

    nodes: dict[int, dict] = {}
    for nid_str, node in raw_nodes.items():
        if nid_str == "root":
            continue
        skill_id = node.get("skill")
        if skill_id is None:
            try:
                skill_id = int(nid_str)
            except ValueError:
                continue
        nodes[skill_id] = node

    return nodes


# Module-level cache (loaded once per process)
_nodes_cache: dict[int, dict] | None = None


def _get_nodes() -> dict[int, dict]:
    global _nodes_cache
    if _nodes_cache is None:
        _nodes_cache = _load_tree_nodes()
    return _nodes_cache


def get_node_stats(
    node_ids: list[int],
    node_overrides: dict[int, str] | None = None,
) -> ParsedMods:
    """Extract all damage-relevant stats from a set of allocated passive nodes.

    Ascendancy notables are skipped here — they are handled by
    ascendancy_effects.py via get_ascendancy_node_names() to avoid
    double-counting complex mechanics.

    If node_overrides is provided (tattoos, runegrafts, conquered mods),
    the override text replaces the base node stats entirely.

    Args:
        node_ids: List of allocated passive tree node IDs.
        node_overrides: Optional dict mapping nodeId → override stat text.

    Returns:
        ParsedMods with all modifiers from the passive tree.
    """
    nodes = _get_nodes()
    overrides = node_overrides or {}
    result = ParsedMods()
    resolved_count = 0

    for nid in node_ids:
        # Check for override (tattoo/runegraft) first
        override_text = overrides.get(nid)
        if override_text:
            stat_texts = [
                line.strip() for line in override_text.splitlines()
                if line.strip() and not line.strip().startswith("Limited to")
            ]
            if stat_texts:
                parsed = parse_mods(stat_texts, source=f"override:{nid}")
                result.merge(parsed)
                resolved_count += 1
            continue

        node = nodes.get(nid)
        if node is None:
            continue

        # Skip ascendancy notables — handled by ascendancy_effects.py
        if node.get("ascendancyName") and node.get("isNotable"):
            continue

        stats = node.get("stats", [])
        if not stats:
            continue

        # Split multi-line stats and rejoin wrapped lines
        stat_texts = _split_stat_lines(stats)
        if not stat_texts:
            continue

        parsed = parse_mods(stat_texts, source=f"tree:{nid}")
        result.merge(parsed)
        resolved_count += 1

    logger.debug(
        "Resolved %d/%d passive nodes with stats",
        resolved_count, len(node_ids),
    )
    return result


def _split_stat_lines(stats: list) -> list[str]:
    """Split multi-line stat strings, rejoining wrapped lines.

    Tree node stats can contain '\\n' that either separates two stats
    or wraps a single stat across lines. If the continuation starts with
    a lowercase letter, it's a wrapped line — rejoin it.
    """
    lines: list[str] = []
    for s in stats:
        if not isinstance(s, str):
            continue
        parts = s.split("\n")
        merged = parts[0].strip()
        for part in parts[1:]:
            part = part.strip()
            if not part:
                continue
            # Continuation line if starts with lowercase (e.g. "to 30% more...")
            if part[0].islower():
                merged = merged.rstrip(",") + " " + part
            else:
                if merged:
                    lines.append(merged)
                merged = part
        if merged:
            lines.append(merged)
    return lines


def get_ascendancy_node_names(node_ids: list[int]) -> list[str]:
    """Identify allocated ascendancy notable names from node IDs.

    Looks up each node ID in the tree cache and returns the names of
    any ascendancy notable passives found.
    """
    nodes = _get_nodes()
    names: list[str] = []
    for nid in node_ids:
        node = nodes.get(nid)
        if node is None:
            continue
        if node.get("ascendancyName") and node.get("isNotable"):
            name = node.get("name", "")
            if name:
                names.append(name)
    return names


def get_node_stat_texts(node_ids: list[int]) -> list[str]:
    """Get raw stat text strings for a set of node IDs (for debugging)."""
    nodes = _get_nodes()
    texts: list[str] = []
    for nid in node_ids:
        node = nodes.get(nid)
        if node is None:
            continue
        for s in node.get("stats", []):
            if isinstance(s, str):
                texts.append(s)
    return texts


def clear_cache() -> None:
    """Clear the module-level node cache (for testing)."""
    global _nodes_cache
    _nodes_cache = None
