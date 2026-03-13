"""Tests for the Client.txt log watcher."""
import pytest
from pop.log_watcher.watcher import LogWatcher, DeathEvent, ZoneEvent, LevelUpEvent
from pop.log_watcher.monster_names import MONSTER_NAMES


@pytest.fixture
def watcher():
    return LogWatcher("/fake/path", monster_names=MONSTER_NAMES)


class TestZoneDetection:
    def test_zone_enter(self, watcher):
        line = '2024/01/15 10:30:00 237826523 b46 [INFO Client 1234] : You have entered Strand Map.'
        watcher._process_line(line)
        assert watcher.stats.current_zone == "Strand Map"
        assert watcher.stats.current_map is not None
        assert watcher.stats.current_map.zone_name == "Strand Map"

    def test_town_enter_ends_map(self, watcher):
        watcher._process_line(
            '2024/01/15 10:30:00 1 b46 [INFO Client 1] : You have entered Strand Map.'
        )
        assert watcher.stats.current_map is not None
        watcher._process_line(
            "2024/01/15 10:35:00 2 b46 [INFO Client 1] : You have entered Lioneye's Watch."
        )
        assert watcher.stats.current_map is None
        assert watcher.stats.maps_completed == 1

    def test_hideout_enter_ends_map(self, watcher):
        watcher._process_line(
            '2024/01/15 10:30:00 1 b46 [INFO Client 1] : You have entered Strand Map.'
        )
        watcher._process_line(
            '2024/01/15 10:35:00 2 b46 [INFO Client 1] : You have entered Celestial Hideout.'
        )
        assert watcher.stats.current_map is None
        assert watcher.stats.maps_completed == 1

    def test_zone_generated_captures_level(self, watcher):
        watcher._process_line(
            '2024/01/15 10:29:58 1 b46 [DEBUG Client 1] Generating level 83 area "MapWorldsStrand" with seed 12345678'
        )
        watcher._process_line(
            '2024/01/15 10:30:00 2 b46 [INFO Client 1] : You have entered Strand Map.'
        )
        assert watcher.stats.current_map is not None
        assert watcher.stats.current_map.area_level == 83


class TestDeathDetection:
    def test_basic_death(self, watcher):
        watcher._process_line(
            '2024/01/15 10:30:00 1 b46 [INFO Client 1] : You have entered Strand Map.'
        )
        watcher._process_line(
            '2024/01/15 10:35:00 2 b46 [INFO Client 1] : MyCharacter has been slain.'
        )
        assert watcher.stats.total_deaths == 1
        assert watcher.stats.last_death is not None
        assert watcher.stats.last_death.character_name == "MyCharacter"
        assert watcher.stats.last_death.zone_name == "Strand Map"

    def test_death_with_killer_detail(self, watcher):
        watcher._process_line(
            '2024/01/15 10:30:00 1 b46 [INFO Client 1] : You have entered Strand Map.'
        )
        watcher._process_line(
            '2024/01/15 10:35:00 2 b46 [INFO Client 1] : MyCharacter has been slain.'
        )
        watcher._process_line(
            '2024/01/15 10:35:00 3 b46 Player died, killer=Metadata/Monsters/InvisibleFire/InvisibleChaostorm (0x1e6cea64090), killer var=x, killer deleted=false, killer destructing=false'
        )
        assert watcher.stats.last_death.killer_name == "Chaos Storm"

    def test_death_with_unknown_killer(self, watcher):
        watcher._process_line(
            '2024/01/15 10:35:00 2 b46 [INFO Client 1] : Exile has been slain.'
        )
        watcher._process_line(
            '2024/01/15 10:35:00 3 b46 Player died, killer=Metadata/Monsters/SomeNew/CrazyBossMonster (0x123), killer var=x, killer deleted=false, killer destructing=false'
        )
        # Should fallback to CamelCase splitting
        assert "Crazy Boss Monster" in watcher.stats.last_death.killer_name

    def test_death_counter_in_map(self, watcher):
        watcher._process_line(
            '2024/01/15 10:30:00 1 b46 [INFO Client 1] : You have entered Strand Map.'
        )
        watcher._process_line(
            '2024/01/15 10:35:00 2 b46 [INFO Client 1] : X has been slain.'
        )
        watcher._process_line(
            '2024/01/15 10:36:00 3 b46 [INFO Client 1] : X has been slain.'
        )
        assert watcher.stats.current_map.deaths == 2
        assert len(watcher.stats.current_map.death_recaps) == 2


class TestLevelUp:
    def test_level_up(self, watcher):
        watcher._process_line(
            '2024/01/15 10:40:00 1 b46 [INFO Client 1] : ExileChar (Ranger) is now level 85'
        )
        assert watcher.stats.levels_gained == 1


class TestMonsterNameResolver:
    def test_known_boss(self, watcher):
        name = watcher._resolve_killer("Metadata/Monsters/AtlasBosses/TheShaperBoss")
        assert name == "The Shaper"

    def test_known_ground_effect(self, watcher):
        name = watcher._resolve_killer("Metadata/Monsters/InvisibleFire/InvisibleChaostorm")
        assert name == "Chaos Storm"

    def test_syndicate_member(self, watcher):
        name = watcher._resolve_killer("Metadata/Monsters/LeagueBetrayal/BetrayalCatarina")
        assert name == "Catarina, Master of Undeath"

    def test_at_suffix_stripped(self, watcher):
        name = watcher._resolve_killer("Metadata/Monsters/BreachBosses/BreachBossFireMap@82")
        assert name == "Xoph, Dark Embers"

    def test_unknown_camelcase_split(self, watcher):
        name = watcher._resolve_killer("Metadata/Monsters/Test/BigScaryDemon")
        assert name == "Big Scary Demon"


class TestBossEncounters:
    def test_boss_zone_starts_encounter(self, watcher):
        watcher._process_line(
            "2024/01/15 10:30:00 1 b46 [INFO Client 1] : You have entered The Shaper's Realm."
        )
        assert watcher.stats.current_boss is not None
        assert watcher.stats.current_boss.boss_name == "The Shaper"

    def test_leaving_boss_zone_counts_kill(self, watcher):
        watcher._process_line(
            "2024/01/15 10:30:00 1 b46 [INFO Client 1] : You have entered The Shaper's Realm."
        )
        watcher._process_line(
            "2024/01/15 10:35:00 2 b46 [INFO Client 1] : You have entered Lioneye's Watch."
        )
        assert watcher.stats.current_boss is None
        assert watcher.stats.boss_kills == 1
        assert len(watcher.stats.boss_encounters) == 1
        assert watcher.stats.boss_encounters[0].killed is True

    def test_death_during_boss(self, watcher):
        watcher._process_line(
            "2024/01/15 10:30:00 1 b46 [INFO Client 1] : You have entered Absence of Value and Meaning."
        )
        watcher._process_line(
            '2024/01/15 10:32:00 2 b46 [INFO Client 1] : X has been slain.'
        )
        assert watcher.stats.current_boss.deaths == 1

    def test_boss_in_dict(self, watcher):
        watcher._process_line(
            "2024/01/15 10:30:00 1 b46 [INFO Client 1] : You have entered The Maven's Crucible."
        )
        d = watcher.stats.to_dict()
        assert d["current_boss"] is not None
        assert d["current_boss"]["boss_name"] == "The Maven"

    def test_boss_history_in_dict(self, watcher):
        watcher._process_line(
            "2024/01/15 10:30:00 1 b46 [INFO Client 1] : You have entered The Shaper's Realm."
        )
        watcher._process_line(
            "2024/01/15 10:35:00 2 b46 [INFO Client 1] : You have entered Lioneye's Watch."
        )
        d = watcher.stats.to_dict()
        assert d["boss_kills"] == 1
        assert len(d["boss_history"]) == 1
        assert d["boss_history"][0]["boss_name"] == "The Shaper"
        assert d["boss_history"][0]["killed"] is True


class TestGraceVerses:
    def test_death_includes_grace_verse(self, watcher):
        watcher._process_line(
            '2024/01/15 10:35:00 2 b46 [INFO Client 1] : MyChar has been slain.'
        )
        assert watcher.stats.last_death.grace_verse != ""
        assert watcher.stats.last_death.grace_ref != ""

    def test_grace_verse_in_dict(self, watcher):
        watcher._process_line(
            '2024/01/15 10:30:00 1 b46 [INFO Client 1] : You have entered Strand Map.'
        )
        watcher._process_line(
            '2024/01/15 10:35:00 2 b46 [INFO Client 1] : X has been slain.'
        )
        d = watcher.stats.to_dict()
        assert d["last_death"]["grace_verse"] != ""
        assert d["last_death"]["grace_ref"] != ""

    def test_death_recap_includes_grace(self, watcher):
        watcher._process_line(
            '2024/01/15 10:30:00 1 b46 [INFO Client 1] : You have entered Strand Map.'
        )
        watcher._process_line(
            '2024/01/15 10:35:00 2 b46 [INFO Client 1] : X has been slain.'
        )
        d = watcher.stats.to_dict()
        assert d["current_map"]["death_recaps"][0]["grace_verse"] != ""


class TestTradeWhispers:
    def test_trade_whisper_parsed(self, watcher):
        watcher._process_line(
            '2024/01/15 10:40:00 1 b46 [INFO Client 1] @From SomePlayer: Hi, I would like to buy your Tabula Rasa Simple Robe listed for 10 chaos in Settlers of Kalguur'
        )
        assert len(watcher.stats.trade_whispers) == 1
        tw = watcher.stats.trade_whispers[0]
        assert tw.player == "SomePlayer"
        assert tw.item == "Tabula Rasa Simple Robe"
        assert tw.price == "10"
        assert tw.currency == "chaos"

    def test_trade_whisper_in_dict(self, watcher):
        watcher._process_line(
            '2024/01/15 10:40:00 1 b46 [INFO Client 1] @From BuyerGuy: Hi, I would like to buy your Headhunter Leather Belt listed for 50 divine in Settlers of Kalguur'
        )
        d = watcher.stats.to_dict()
        assert len(d["trade_whispers"]) == 1
        assert d["trade_whispers"][0]["player"] == "BuyerGuy"
        assert d["trade_whispers"][0]["item"] == "Headhunter Leather Belt"
        assert d["trade_whispers"][0]["price"] == "50"
        assert d["trade_whispers"][0]["currency"] == "divine"


class TestSessionStats:
    def test_to_dict(self, watcher):
        watcher._process_line(
            '2024/01/15 10:30:00 1 b46 [INFO Client 1] : You have entered Strand Map.'
        )
        watcher._process_line(
            '2024/01/15 10:35:00 2 b46 [INFO Client 1] : X has been slain.'
        )
        d = watcher.stats.to_dict()
        assert d["total_deaths"] == 1
        assert d["current_map"] is not None
        assert d["current_map"]["zone_name"] == "Strand Map"
        assert d["last_death"]["killer"] == "Unknown"
        assert d["current_zone"] == "Strand Map"
        assert d["map_history"] == []
        assert d["fastest_map"] is None
        assert d["deadliest_map"] is None

    def test_map_history_after_completion(self, watcher):
        watcher._process_line(
            '2024/01/15 10:30:00 1 b46 [INFO Client 1] : You have entered Strand Map.'
        )
        watcher._process_line(
            '2024/01/15 10:35:00 2 b46 [INFO Client 1] : X has been slain.'
        )
        watcher._process_line(
            '2024/01/15 10:36:00 3 b46 [INFO Client 1] : You have entered Glacier Map.'
        )
        d = watcher.stats.to_dict()
        assert d["maps_completed"] == 1
        assert len(d["map_history"]) == 1
        assert d["map_history"][0]["zone_name"] == "Strand Map"
        assert d["map_history"][0]["deaths"] == 1
        assert d["fastest_map"] is not None
        assert d["fastest_map"]["zone_name"] == "Strand Map"
        assert d["deadliest_map"]["zone_name"] == "Strand Map"

    def test_fastest_map_picks_shortest(self, watcher):
        import time
        # Map 1: Strand — manually set times to simulate real durations
        watcher._process_line(
            '2024/01/15 10:30:00 1 b46 [INFO Client 1] : You have entered Strand Map.'
        )
        watcher.stats.current_map.start_time = time.time() - 300  # 5 min ago
        watcher._process_line(
            "2024/01/15 10:35:00 2 b46 [INFO Client 1] : You have entered Lioneye's Watch."
        )
        # Map 2: Glacier — shorter run
        watcher._process_line(
            '2024/01/15 10:36:00 3 b46 [INFO Client 1] : You have entered Glacier Map.'
        )
        watcher.stats.current_map.start_time = time.time() - 120  # 2 min ago
        watcher._process_line(
            "2024/01/15 10:37:00 4 b46 [INFO Client 1] : You have entered Lioneye's Watch."
        )
        d = watcher.stats.to_dict()
        assert d["maps_completed"] == 2
        assert len(d["map_history"]) == 2
        # Glacier should be fastest (shorter duration)
        assert d["fastest_map"]["zone_name"] == "Glacier Map"
        # History is most-recent first
        assert d["map_history"][0]["zone_name"] == "Glacier Map"
        assert d["map_history"][1]["zone_name"] == "Strand Map"
