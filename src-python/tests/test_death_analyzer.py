"""Tests for death analyzer."""

from pop.price_check.death_analyzer import analyze_death


class TestAnalyzeDeath:
    def _make_defence(self, **overrides) -> dict:
        """Create a defence dict with defaults."""
        base = {
            "life": 5000,
            "energy_shield": 0,
            "armour": 15000,
            "evasion": 10000,
            "block_chance": 50,
            "spell_block_chance": 30,
            "spell_suppression": 100,
            "phys_damage_reduction": 8,
            "elemental_resistances": {"fire": 75, "cold": 75, "lightning": 75},
            "chaos_resistance": 20,
        }
        base.update(overrides)
        return base

    def _make_death_event(self, killer: str = "Kitava", zone: str = "The Canals") -> dict:
        return {"killer": killer, "zone": zone, "timestamp": "2026-03-17 10:00:00"}

    def test_healthy_build_no_weaknesses(self):
        result = analyze_death(self._make_death_event(), self._make_defence())
        assert result["killer"] == "Kitava"
        assert result["zone"] == "The Canals"
        assert len(result["weaknesses"]) == 0

    def test_low_life_flagged(self):
        result = analyze_death(
            self._make_death_event(),
            self._make_defence(life=3500),
        )
        weaknesses = result["weaknesses"]
        assert any(w["stat"] == "Life" for w in weaknesses)

    def test_uncapped_fire_res(self):
        result = analyze_death(
            self._make_death_event(),
            self._make_defence(elemental_resistances={"fire": 45, "cold": 75, "lightning": 75}),
        )
        weaknesses = result["weaknesses"]
        fire_weak = [w for w in weaknesses if w["stat"] == "Fire Resistance"]
        assert len(fire_weak) == 1
        assert fire_weak[0]["current"] == 45
        assert fire_weak[0]["target"] == 75

    def test_negative_chaos_res_flagged(self):
        result = analyze_death(
            self._make_death_event(),
            self._make_defence(chaos_resistance=-40),
        )
        weaknesses = result["weaknesses"]
        assert any(w["stat"] == "Chaos Resistance" for w in weaknesses)
        assert any("chaos" in s.lower() for s in result["suggestions"])

    def test_low_suppression_flagged(self):
        result = analyze_death(
            self._make_death_event(),
            self._make_defence(spell_suppression=30, energy_shield=0),
        )
        weaknesses = result["weaknesses"]
        assert any(w["stat"] == "Spell Suppression" for w in weaknesses)

    def test_es_build_no_suppression_warning(self):
        """ES builds (high ES) should not get spell suppression warnings."""
        result = analyze_death(
            self._make_death_event(),
            self._make_defence(spell_suppression=0, energy_shield=5000),
        )
        weaknesses = result["weaknesses"]
        assert not any(w["stat"] == "Spell Suppression" for w in weaknesses)

    def test_boss_zone_higher_thresholds(self):
        """Boss zones use higher life threshold (5500)."""
        result = analyze_death(
            self._make_death_event(zone="The Shaper's Realm"),
            self._make_defence(life=5000),
        )
        weaknesses = result["weaknesses"]
        assert any(w["stat"] == "Life" for w in weaknesses)

    def test_normal_zone_lower_thresholds(self):
        """Normal maps use lower life threshold (4000)."""
        result = analyze_death(
            self._make_death_event(zone="Strand Map"),
            self._make_defence(life=4500),
        )
        weaknesses = result["weaknesses"]
        assert not any(w["stat"] == "Life" for w in weaknesses)

    def test_grace_verse_included(self):
        result = analyze_death(self._make_death_event(), self._make_defence())
        assert result["grace_verse"]
        assert result["grace_ref"]

    def test_zone_override(self):
        result = analyze_death(
            self._make_death_event(zone="somewhere"),
            self._make_defence(),
            zone_name="Override Zone",
        )
        assert result["zone"] == "Override Zone"

    def test_max_three_suggestions(self):
        """Even with many weaknesses, suggestions are capped at 3."""
        result = analyze_death(
            self._make_death_event(zone="The Shaper's Realm"),
            self._make_defence(
                life=2500,
                elemental_resistances={"fire": 30, "cold": 20, "lightning": 10},
                chaos_resistance=-60,
                spell_suppression=0,
                energy_shield=0,
                armour=2000,
            ),
        )
        assert len(result["suggestions"]) <= 3

    def test_low_armour_boss_zone(self):
        result = analyze_death(
            self._make_death_event(zone="The Maven's Crucible"),
            self._make_defence(armour=5000),
        )
        weaknesses = result["weaknesses"]
        assert any(w["stat"] == "Armour" for w in weaknesses)

    def test_element_from_monster_elements_dict(self):
        """MONSTER_ELEMENTS lookup should override keyword matching."""
        result = analyze_death(
            {"killer": "The Shaper", "killer_raw": "Metadata/Monsters/AtlasBosses/TheShaperBoss", "zone": "The Shaper's Realm"},
            self._make_defence(),
        )
        assert result["damage_element"] == "Cold"

    def test_element_from_keywords(self):
        result = analyze_death(
            {"killer": "Unknown Frost Wraith", "killer_raw": "Metadata/Monsters/SomeNew/FrostWraith", "zone": "Strand Map"},
            self._make_defence(),
        )
        assert result["damage_element"] == "Cold"

    def test_element_from_boss_zone_fallback(self):
        """When killer is unknown, element should come from boss zone."""
        result = analyze_death(
            {"killer": "Unknown", "killer_raw": "", "zone": "The Shaper's Realm"},
            self._make_defence(),
        )
        assert result["damage_element"] == "Cold"

    def test_element_suggestion_for_fire_death(self):
        """Dying to fire damage with uncapped fire res should mention it."""
        result = analyze_death(
            {"killer": "Guardian of the Phoenix", "killer_raw": "Metadata/Monsters/AtlasBosses/PhoenixBoss", "zone": "Phoenix Map"},
            self._make_defence(elemental_resistances={"fire": 50, "cold": 75, "lightning": 75}),
        )
        assert result["damage_element"] == "Fire"
        assert any("Fire" in s and "fire" in s.lower() for s in result["suggestions"])
