"""
Client.txt log file watcher for Path of Exile.

Tails the PoE Client.txt log file and emits structured events
for zone changes, deaths, level ups, trade whispers, etc.
"""
from __future__ import annotations

import os
import random
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from pop.log_watcher.grace_verses import DEATH_VERSES

# --- Event models ---

@dataclass
class ZoneEvent:
    timestamp: str
    zone_name: str
    is_town: bool = False
    is_hideout: bool = False

@dataclass
class ZoneGeneratedEvent:
    timestamp: str
    area_level: int
    area_id: str
    seed: int

@dataclass
class DeathEvent:
    timestamp: str
    character_name: str
    killer_raw: str = ""        # raw metadata path
    killer_name: str = ""       # human-readable name
    zone_name: str = ""         # zone where death occurred
    grace_verse: str = ""       # encouraging Bible verse
    grace_ref: str = ""         # verse reference (e.g. "Psalm 23:4")

@dataclass
class LevelUpEvent:
    timestamp: str
    character_name: str
    char_class: str
    level: int

@dataclass
class TradeWhisperEvent:
    timestamp: str
    player: str
    item: str
    price: str
    currency: str
    league: str
    stash_tab: str = ""

@dataclass
class BossEncounter:
    boss_name: str
    zone_name: str
    start_time: float = 0.0
    end_time: float = 0.0
    deaths: int = 0
    killed: bool = False  # True if player left zone alive (assumed kill)

    @property
    def duration_seconds(self) -> float:
        if self.end_time > 0:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    @property
    def duration_display(self) -> str:
        secs = int(self.duration_seconds)
        m, s = divmod(secs, 60)
        if m > 0:
            return f"{m}m {s}s"
        return f"{s}s"

@dataclass
class MapRun:
    zone_name: str
    area_level: int = 0
    start_time: float = 0.0
    end_time: float = 0.0
    deaths: int = 0
    death_recaps: list[DeathEvent] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float:
        if self.end_time > 0:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    @property
    def duration_display(self) -> str:
        secs = int(self.duration_seconds)
        m, s = divmod(secs, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h}h {m}m {s}s"
        return f"{m}m {s}s"

@dataclass
class SessionStats:
    maps_completed: int = 0
    total_deaths: int = 0
    levels_gained: int = 0
    session_start: float = 0.0
    map_runs: list[MapRun] = field(default_factory=list)
    current_map: MapRun | None = None
    current_zone: str = ""
    last_death: DeathEvent | None = None
    trade_whispers: list[TradeWhisperEvent] = field(default_factory=list)
    boss_encounters: list[BossEncounter] = field(default_factory=list)
    current_boss: BossEncounter | None = None
    boss_kills: int = 0

    @property
    def maps_per_hour(self) -> float:
        elapsed = time.time() - self.session_start
        if elapsed < 60 or self.maps_completed == 0:
            return 0.0
        return self.maps_completed / (elapsed / 3600)

    @property
    def avg_map_time(self) -> str:
        completed = [r for r in self.map_runs if r.end_time > 0]
        if not completed:
            return "—"
        avg = sum(r.duration_seconds for r in completed) / len(completed)
        m, s = divmod(int(avg), 60)
        return f"{m}m {s}s"

    @property
    def deaths_per_hour(self) -> float:
        elapsed = time.time() - self.session_start
        if elapsed < 60 or self.total_deaths == 0:
            return 0.0
        return self.total_deaths / (elapsed / 3600)

    def to_dict(self) -> dict:
        current = None
        if self.current_map:
            current = {
                "zone_name": self.current_map.zone_name,
                "area_level": self.current_map.area_level,
                "duration": self.current_map.duration_display,
                "deaths": self.current_map.deaths,
                "death_recaps": [
                    {
                        "killer": d.killer_name or d.killer_raw,
                        "timestamp": d.timestamp,
                        "grace_verse": d.grace_verse,
                        "grace_ref": d.grace_ref,
                    }
                    for d in self.current_map.death_recaps
                ],
            }

        last_death = None
        if self.last_death:
            last_death = {
                "character": self.last_death.character_name,
                "killer": self.last_death.killer_name or self.last_death.killer_raw or "Unknown",
                "zone": self.last_death.zone_name,
                "timestamp": self.last_death.timestamp,
                "grace_verse": self.last_death.grace_verse,
                "grace_ref": self.last_death.grace_ref,
            }

        # Completed map history (most recent first, last 20)
        completed = [r for r in self.map_runs if r.end_time > 0]
        history = []
        for r in reversed(completed[-20:]):
            secs = int(r.duration_seconds)
            m, s = divmod(secs, 60)
            history.append({
                "zone_name": r.zone_name,
                "area_level": r.area_level,
                "duration": f"{m}m {s}s",
                "duration_seconds": secs,
                "deaths": r.deaths,
            })

        fastest = None
        deadliest = None
        if completed:
            f = min(completed, key=lambda r: r.duration_seconds)
            fm, fs = divmod(int(f.duration_seconds), 60)
            fastest = {"zone_name": f.zone_name, "area_level": f.area_level, "duration": f"{fm}m {fs}s", "duration_seconds": int(f.duration_seconds)}
            d = max(completed, key=lambda r: r.deaths)
            if d.deaths > 0:
                deadliest = {"zone_name": d.zone_name, "area_level": d.area_level, "deaths": d.deaths}

        # Recent trade whispers (last 10, most recent first)
        trades = []
        for tw in reversed(self.trade_whispers[-10:]):
            trades.append({
                "timestamp": tw.timestamp,
                "player": tw.player,
                "item": tw.item,
                "price": tw.price,
                "currency": tw.currency,
                "league": tw.league,
            })

        # Boss encounter info
        current_boss = None
        if self.current_boss:
            current_boss = {
                "boss_name": self.current_boss.boss_name,
                "zone_name": self.current_boss.zone_name,
                "duration": self.current_boss.duration_display,
                "duration_seconds": int(self.current_boss.duration_seconds),
                "deaths": self.current_boss.deaths,
            }

        boss_history = []
        for be in reversed(self.boss_encounters[-10:]):
            boss_history.append({
                "boss_name": be.boss_name,
                "zone_name": be.zone_name,
                "duration": be.duration_display,
                "duration_seconds": int(be.duration_seconds),
                "deaths": be.deaths,
                "killed": be.killed,
            })

        # Session time played
        elapsed = time.time() - self.session_start
        h, rem = divmod(int(elapsed), 3600)
        m_t, s_t = divmod(rem, 60)
        time_played = f"{h}h {m_t}m" if h > 0 else f"{m_t}m {s_t}s"

        return {
            "maps_completed": self.maps_completed,
            "total_deaths": self.total_deaths,
            "levels_gained": self.levels_gained,
            "maps_per_hour": round(self.maps_per_hour, 1),
            "avg_map_time": self.avg_map_time,
            "deaths_per_hour": round(self.deaths_per_hour, 1),
            "current_map": current,
            "last_death": last_death,
            "current_zone": self.current_zone,
            "map_history": history,
            "fastest_map": fastest,
            "deadliest_map": deadliest,
            "trade_whispers": trades,
            "trades_completed": len(self.trade_whispers),
            "current_boss": current_boss,
            "boss_kills": self.boss_kills,
            "boss_history": boss_history,
            "time_played": time_played,
        }


# --- Regex patterns ---

RE_TIMESTAMP = r"(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})"

RE_ZONE_ENTER = re.compile(
    RE_TIMESTAMP + r".*\[INFO Client \d+\] : You have entered (.+)\."
)

RE_ZONE_GENERATED = re.compile(
    RE_TIMESTAMP + r'.*\[DEBUG Client \d+\] Generating level (\d+) area "([^"]+)" with seed (\d+)'
)

RE_DEATH_SLAIN = re.compile(
    RE_TIMESTAMP + r".*\[INFO Client \d+\] : (.+) has been slain\."
)

RE_DEATH_DETAIL = re.compile(
    r".*Player died, killer=([^\s(]+)"
)

RE_LEVEL_UP = re.compile(
    RE_TIMESTAMP + r".*\[INFO Client \d+\] : (.+) \((\w+)\) is now level (\d+)"
)

RE_TRADE_WHISPER = re.compile(
    RE_TIMESTAMP + r".*\[INFO Client \d+\] @From (?:<[^>]+> )?(.+?): Hi, I would like to buy your (.+?) listed for ([\d.]+) (.+?) in (.+?)(?:\(stash tab \"([^\"]*)\";.*\))?"
)

# Towns and hideouts
TOWNS = {
    "Lioneye's Watch", "The Forest Encampment", "The Sarn Encampment",
    "Highgate", "Overseer's Tower", "The Bridge Encampment",
    "Oriath Docks", "Oriath", "Karui Shores",
    "The Rogue Harbour",
}

HIDEOUT_PATTERN = re.compile(r"(?:Hideout|hideout)", re.IGNORECASE)

# Boss encounter zones — zone name -> boss display name
BOSS_ZONES: dict[str, str] = {
    # PoE 1 endgame
    "The Shaper's Realm": "The Shaper",
    "Absence of Value and Meaning": "Sirus, Awakener of Worlds",
    "The Maven's Crucible": "The Maven",
    "Eye of the Storm": "Sirus, Awakener of Worlds",
    "The Elder's Domain": "The Elder",
    "Absence of Symmetry and Harmony": "The Uber Elder",
    "The Feared": "The Feared (Invitation)",
    "The Formed": "The Formed (Invitation)",
    "The Twisted": "The Twisted (Invitation)",
    "The Forgotten": "The Forgotten (Invitation)",
    "The Hidden": "The Hidden (Invitation)",
    "The Elderslayers": "The Elderslayers (Invitation)",
    # Uber bosses
    "The Shaper's Realm (Uber)": "Uber Shaper",
    # Atlas bosses
    "Searing Exarch Arena": "The Searing Exarch",
    "The Eater of Worlds' Arena": "The Eater of Worlds",
    "Black Star Arena": "The Black Star",
    "The Infinite Hunger Arena": "The Infinite Hunger",
    # Breach lords
    "Xoph's Domain": "Xoph, Dark Embers",
    "Tul's Domain": "Tul, Creeping Avalanche",
    "Esh's Domain": "Esh, Forked Thought",
    "Uul-Netol's Domain": "Uul-Netol, Unburdened Flesh",
    "Chayula's Domain": "Chayula, Who Dreamt",
    # Campaign
    "The Cathedral Rooftop": "Kitava",
    "The Feeding Trough": "Kitava (Act 10)",
    # Simulacrum
    "Simulacrum": "Simulacrum",
    # PoE 2
    "The Arbiter of Ash Arena": "The Arbiter of Ash",
}


# --- Log Watcher ---

class LogWatcher:
    """Watches PoE Client.txt and tracks session stats."""

    def __init__(
        self,
        log_path: str | Path,
        monster_names: dict[str, str] | None = None,
        on_death: Callable[[DeathEvent], None] | None = None,
        on_zone: Callable[[ZoneEvent], None] | None = None,
        on_level_up: Callable[[LevelUpEvent], None] | None = None,
    ):
        self.log_path = Path(log_path)
        self.monster_names = monster_names or {}
        self.on_death = on_death
        self.on_zone = on_zone
        self.on_level_up = on_level_up

        self.stats = SessionStats(session_start=time.time())
        self._pending_area_level: int = 0
        self._pending_area_id: str = ""
        self._running = False

    def _resolve_killer(self, raw: str) -> str:
        """Convert metadata path to readable name."""
        # Direct lookup
        if raw in self.monster_names:
            return self.monster_names[raw]

        # Try matching by suffix (metadata paths vary per instance)
        # e.g. "Metadata/Monsters/Daemon/BreachBossFire@82" -> strip @N suffix
        clean = re.sub(r"@\d+$", "", raw)
        if clean in self.monster_names:
            return self.monster_names[clean]

        # Extract last meaningful part
        # "Metadata/Monsters/InvisibleFire/InvisibleChaosstorm" -> "Invisible Chaostorm"
        parts = clean.rstrip("/").split("/")
        if parts:
            name = parts[-1]
            # CamelCase to spaces
            name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
            # Remove common prefixes
            for prefix in ("Invisible", "Monster"):
                if name.startswith(prefix) and len(name) > len(prefix):
                    name = name[len(prefix):].strip()
            return name or raw

        return raw

    def _is_town_or_hideout(self, zone: str) -> tuple[bool, bool]:
        is_town = zone in TOWNS
        is_hideout = bool(HIDEOUT_PATTERN.search(zone))
        return is_town, is_hideout

    def _is_map_zone(self, zone: str) -> bool:
        is_town, is_hideout = self._is_town_or_hideout(zone)
        return not is_town and not is_hideout

    def _handle_zone_enter(self, timestamp: str, zone_name: str) -> None:
        is_town, is_hideout = self._is_town_or_hideout(zone_name)

        # End current boss encounter if leaving boss zone
        if self.stats.current_boss and zone_name != self.stats.current_boss.zone_name:
            self.stats.current_boss.end_time = time.time()
            # If player left alive (went to town/hideout/new zone), count as kill
            self.stats.current_boss.killed = True
            self.stats.boss_kills += 1
            self.stats.boss_encounters.append(self.stats.current_boss)
            self.stats.current_boss = None

        # End current map run if we're leaving a map
        if self.stats.current_map and (is_town or is_hideout or zone_name != self.stats.current_zone):
            self.stats.current_map.end_time = time.time()
            self.stats.map_runs.append(self.stats.current_map)
            self.stats.maps_completed += 1
            self.stats.current_map = None

        self.stats.current_zone = zone_name

        # Start a new map run if this is a map zone
        if self._is_map_zone(zone_name):
            self.stats.current_map = MapRun(
                zone_name=zone_name,
                area_level=self._pending_area_level,
                start_time=time.time(),
            )
            self._pending_area_level = 0
            self._pending_area_id = ""

        # Start boss encounter if entering a boss zone
        if zone_name in BOSS_ZONES:
            self.stats.current_boss = BossEncounter(
                boss_name=BOSS_ZONES[zone_name],
                zone_name=zone_name,
                start_time=time.time(),
            )

        event = ZoneEvent(
            timestamp=timestamp,
            zone_name=zone_name,
            is_town=is_town,
            is_hideout=is_hideout,
        )
        if self.on_zone:
            self.on_zone(event)

    def _handle_death(self, timestamp: str, character_name: str, killer_raw: str = "") -> None:
        killer_name = self._resolve_killer(killer_raw) if killer_raw else ""

        ref, verse = random.choice(DEATH_VERSES)
        event = DeathEvent(
            timestamp=timestamp,
            character_name=character_name,
            killer_raw=killer_raw,
            killer_name=killer_name,
            zone_name=self.stats.current_zone,
            grace_verse=verse,
            grace_ref=ref,
        )

        self.stats.total_deaths += 1
        self.stats.last_death = event

        if self.stats.current_map:
            self.stats.current_map.deaths += 1
            self.stats.current_map.death_recaps.append(event)

        if self.stats.current_boss:
            self.stats.current_boss.deaths += 1

        if self.on_death:
            self.on_death(event)

    def _process_line(self, line: str) -> None:
        # Zone generated (DEBUG) — comes before zone enter
        m = RE_ZONE_GENERATED.match(line)
        if m:
            self._pending_area_level = int(m.group(2))
            self._pending_area_id = m.group(3)
            return

        # Zone entered
        m = RE_ZONE_ENTER.match(line)
        if m:
            self._handle_zone_enter(m.group(1), m.group(2))
            return

        # Death (slain)
        m = RE_DEATH_SLAIN.match(line)
        if m:
            self._handle_death(m.group(1), m.group(2))
            return

        # Death detail (killer metadata)
        m = RE_DEATH_DETAIL.match(line)
        if m and self.stats.last_death and not self.stats.last_death.killer_raw:
            killer_raw = m.group(1)
            self.stats.last_death.killer_raw = killer_raw
            self.stats.last_death.killer_name = self._resolve_killer(killer_raw)
            # Also update the map's death recap
            if self.stats.current_map and self.stats.current_map.death_recaps:
                last = self.stats.current_map.death_recaps[-1]
                last.killer_raw = killer_raw
                last.killer_name = self.stats.last_death.killer_name
            return

        # Level up
        m = RE_LEVEL_UP.match(line)
        if m:
            event = LevelUpEvent(
                timestamp=m.group(1),
                character_name=m.group(2),
                char_class=m.group(3),
                level=int(m.group(4)),
            )
            self.stats.levels_gained += 1
            if self.on_level_up:
                self.on_level_up(event)
            return

        # Trade whisper
        m = RE_TRADE_WHISPER.match(line)
        if m:
            event = TradeWhisperEvent(
                timestamp=m.group(1),
                player=m.group(2),
                item=m.group(3),
                price=m.group(4),
                currency=m.group(5),
                league=m.group(6),
                stash_tab=m.group(7) or "",
            )
            self.stats.trade_whispers.append(event)
            return

    def start(self, poll_interval: float = 0.5) -> None:
        """Start tailing the log file. Blocks until stop() is called."""
        if not self.log_path.exists():
            raise FileNotFoundError(f"Log file not found: {self.log_path}")

        self._running = True

        with open(self.log_path, "r", encoding="utf-8", errors="replace") as f:
            # Seek to end — only process new lines
            f.seek(0, os.SEEK_END)

            while self._running:
                line = f.readline()
                if line:
                    line = line.strip()
                    if line:
                        self._process_line(line)
                else:
                    time.sleep(poll_interval)

    def stop(self) -> None:
        self._running = False
