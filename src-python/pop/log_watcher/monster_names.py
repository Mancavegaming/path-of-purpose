"""
Mapping of PoE monster metadata paths to human-readable names.

These appear in the Client.txt DEBUG line:
  Player died, killer=Metadata/Monsters/...

The watcher falls back to CamelCase splitting for unknown paths,
so this dict only needs the non-obvious or important ones.
~200 entries covering endgame bosses, on-death effects, league mechanics, etc.
"""

MONSTER_NAMES: dict[str, str] = {
    # ── On-death effects & ground hazards (most common killers) ───────
    "Metadata/Monsters/InvisibleFire/InvisibleChaosstorm": "Chaos Storm",
    "Metadata/Monsters/InvisibleFire/InvisibleChaostorm": "Chaos Storm",
    "Metadata/Monsters/InvisibleFire/InvisibleFireAfterDeath": "On-Death Explosion",
    "Metadata/Monsters/InvisibleFire/AfterDeathFireDegen": "On-Death Fire",
    "Metadata/Monsters/InvisibleFire/AfterDeathColdDegen": "On-Death Cold",
    "Metadata/Monsters/InvisibleFire/AfterDeathChaosDegen": "On-Death Chaos",
    "Metadata/Monsters/InvisibleFire/InvisibleFireDegen": "Burning Ground",
    "Metadata/Monsters/InvisibleFire/InvisibleCausticGround": "Caustic Ground",
    "Metadata/Monsters/InvisibleFire/InvisibleChilledGround": "Chilled Ground",
    "Metadata/Monsters/InvisibleFire/InvisibleShockedGround": "Shocked Ground",
    "Metadata/Monsters/InvisibleFire/InvisibleDesecrate": "Desecrated Ground",
    "Metadata/Monsters/InvisibleFire/InvisibleProfaneGround": "Profane Ground",
    "Metadata/Monsters/InvisibleFire/InvisibleTarGround": "Tar Ground",
    "Metadata/Monsters/InvisibleFire/InvisibleSandstorm": "Sandstorm",
    "Metadata/Monsters/InvisibleFire/InvisibleFireRighteousFire": "Righteous Fire (Monster)",
    "Metadata/Monsters/InvisibleFire/InvisibleFireRighteousFireMetamorphosis": "Creeping Fire",
    "Metadata/Monsters/InvisibleFire/InvisibleFireStormcallMapBoss": "Storm Call (Boss)",
    "Metadata/Monsters/InvisibleFire/InvisibleFireColdSnapMap": "Cold Snap Ground",
    "Metadata/Monsters/InvisibleFire/InvisibleFireAfflictionDemonColdDegen": "Cold Snap Ground (Delirium)",
    "Metadata/Monsters/InvisibleFire/InvisibleFireAfflictionDemonFireDegen": "Fire Ground (Delirium)",
    "Metadata/Monsters/InvisibleFire/InvisibleFrostboltDegen": "Frostbolt Ground",
    "Metadata/Monsters/InvisibleFire/InvisibleFireMortarDegen": "Fire Mortar Ground",

    # ── Bearers & Volatiles ───────────────────────────────────────────
    "Metadata/Monsters/Daemon/BearerOfTheGuardian": "Bearer of the Guardian",
    "Metadata/Monsters/Daemon/BearerOfTorment": "Bearer of Torment",
    "Metadata/Monsters/Daemon/BearerOfBlessing": "Bearer of Blessing",
    "Metadata/Monsters/Daemon/BearerOfFragility": "Bearer of Fragility",
    "Metadata/Monsters/Daemon/DaemonBearerOfFlame": "Bearer of the Flame",
    "Metadata/Monsters/Daemon/DaemonBearerOfFrost": "Bearer of Frost",
    "Metadata/Monsters/Daemon/DaemonBearerOfLightning": "Bearer of Lightning",
    "Metadata/Monsters/Daemon/DaemonBearerOfBlood": "Bearer of Blood",
    "Metadata/Monsters/Daemon/DaemonBearerOfGuardians": "Bearer of Guardians",
    "Metadata/Monsters/Daemon/VolatileCoreFire": "Volatile Flamblood",
    "Metadata/Monsters/Daemon/VolatileCoreCold": "Volatile Frostblood",
    "Metadata/Monsters/Daemon/VolatileCoreLightning": "Volatile Stormblood",
    "Metadata/Monsters/Daemon/VolatileCorePhysical": "Volatile Boneblood",
    "Metadata/Monsters/Daemon/VolatileCoreChaos": "Volatile Voidblood",
    "Metadata/Monsters/VolatileCore/VolatileCore": "Volatile Flamblood",
    "Metadata/Monsters/VolatileCore/VolatileDeadCore": "Volatile Dead Core",

    # ── Boss damage sources (daemons) ─────────────────────────────────
    "Metadata/Monsters/Daemon/DaemonShaperBeam": "Shaper Beam",
    "Metadata/Monsters/Daemon/DaemonShaperBall": "Shaper Ball",
    "Metadata/Monsters/Daemon/DaemonSirusMeteor": "Sirus Die Beam",
    "Metadata/Monsters/Daemon/DaemonMaven": "Maven Cascade",
    "Metadata/Monsters/Daemon/DaemonElderShockNova": "Elder Shock Nova",
    "Metadata/Monsters/Daemon/MoltenShellDaemon": "Molten Shell Explosion",
    "Metadata/Monsters/Daemon/DaemonLabyrinthTrap": "Labyrinth Trap",
    "Metadata/Monsters/Daemon/BreachBossFire": "Breach Fire Daemon",

    # ── Endgame bosses ────────────────────────────────────────────────
    "Metadata/Monsters/AtlasBosses/TheShaperBoss": "The Shaper",
    "Metadata/Monsters/AtlasBosses/TheShaperBossUberElder": "The Shaper (Uber Elder)",
    "Metadata/Monsters/AtlasBosses/TheElder": "The Elder",
    "Metadata/Monsters/AtlasBosses/TheElderBoss": "The Elder",
    "Metadata/Monsters/AtlasBosses/TheElderBossEscaped": "The Elder (Uber)",
    "Metadata/Monsters/AtlasBosses/TheElderUber": "The Elder (Uber)",
    "Metadata/Monsters/AtlasExiles/AtlasExile1": "Al-Hezmin, the Hunter",
    "Metadata/Monsters/AtlasExiles/AtlasExile2": "Veritania, the Redeemer",
    "Metadata/Monsters/AtlasExiles/AtlasExile3": "Drox, the Warlord",
    "Metadata/Monsters/AtlasExiles/AtlasExile4": "Baran, the Crusader",
    "Metadata/Monsters/AtlasExiles/AtlasExile5": "Sirus, Awakener of Worlds",
    "Metadata/Monsters/AtlasExiles/AtlasExile5Throne": "Sirus, Awakener of Worlds",
    "Metadata/Monsters/AtlasExiles/AtlasExile1Uber": "Al-Hezmin, the Hunter (Uber)",
    "Metadata/Monsters/AtlasExiles/AtlasExile2Uber": "Veritania, the Redeemer (Uber)",
    "Metadata/Monsters/AtlasExiles/AtlasExile3Uber": "Drox, the Warlord (Uber)",
    "Metadata/Monsters/AtlasExiles/AtlasExile4Uber": "Baran, the Crusader (Uber)",
    "Metadata/Monsters/AtlasExiles/AtlasExile5Uber": "Sirus, Awakener of Worlds (Uber)",
    "Metadata/Monsters/MavenBoss/TheMaven": "The Maven",
    "Metadata/Monsters/MavenBoss/TheMavenEnraged": "The Maven (Enraged)",
    "Metadata/Monsters/AtlasInvaders/CleansingBoss": "The Searing Exarch",
    "Metadata/Monsters/AtlasInvaders/ConsumeBoss": "The Eater of Worlds",
    "Metadata/Monsters/AtlasInvaders/BlackStarBoss": "The Black Star",
    "Metadata/Monsters/AtlasInvaders/DoomBoss": "The Infinite Hunger",
    "Metadata/Monsters/AtlasBosses/SearingExarch": "The Searing Exarch",
    "Metadata/Monsters/AtlasBosses/EaterOfWorlds": "The Eater of Worlds",
    "Metadata/Monsters/AtlasBosses/TheBlackStar": "The Black Star",
    "Metadata/Monsters/AtlasBosses/TheInfiniteHunger": "The Infinite Hunger",

    # ── Shaper guardians ──────────────────────────────────────────────
    "Metadata/Monsters/AtlasBosses/ShaperGuardianPhoenix": "Guardian of the Phoenix",
    "Metadata/Monsters/AtlasBosses/ShaperGuardianMinotaur": "Guardian of the Minotaur",
    "Metadata/Monsters/AtlasBosses/ShaperGuardianChimera": "Guardian of the Chimera",
    "Metadata/Monsters/AtlasBosses/ShaperGuardianHydra": "Guardian of the Hydra",
    "Metadata/Monsters/AtlasBosses/PhoenixBoss": "Guardian of the Phoenix",
    "Metadata/Monsters/AtlasBosses/MinotaurBoss": "Guardian of the Minotaur",
    "Metadata/Monsters/AtlasBosses/ChimeraBoss": "Guardian of the Chimera",
    "Metadata/Monsters/AtlasBosses/HydraBoss": "Guardian of the Hydra",

    # ── Elder guardians ───────────────────────────────────────────────
    "Metadata/Monsters/AtlasBosses/ElderGuardianPurifier": "The Purifier",
    "Metadata/Monsters/AtlasBosses/ElderGuardianConstrictor": "The Constrictor",
    "Metadata/Monsters/AtlasBosses/ElderGuardianEnslaverBoss": "The Enslaver",
    "Metadata/Monsters/AtlasBosses/ElderGuardianEradicator": "The Eradicator",

    # ── Atziri ────────────────────────────────────────────────────────
    "Metadata/Monsters/Atziri/Atziri": "Atziri, Queen of the Vaal",
    "Metadata/Monsters/Atziri/Atziri2": "Atziri, Queen of the Vaal (Uber)",
    "Metadata/Monsters/Atziri/AtziriUber": "Atziri, Queen of the Vaal (Uber)",

    # ── Breach bosses ─────────────────────────────────────────────────
    "Metadata/Monsters/BreachBosses/BreachBossFireMap": "Xoph, Dark Embers",
    "Metadata/Monsters/BreachBosses/BreachBossColdMap": "Tul, Creeping Avalanche",
    "Metadata/Monsters/BreachBosses/BreachBossLightningMap": "Esh, Forked Thought",
    "Metadata/Monsters/BreachBosses/BreachBossPhysicalMap": "Uul-Netol, Unburdened Flesh",
    "Metadata/Monsters/BreachBosses/BreachBossChaosMap": "Chayula, Who Dreamt",
    "Metadata/Monsters/BreachBosses/BreachBossFire": "Xoph, Dark Embers",
    "Metadata/Monsters/BreachBosses/BreachBossCold": "Tul, Creeping Avalanche",
    "Metadata/Monsters/BreachBosses/BreachBossLightning": "Esh, Forked Thought",
    "Metadata/Monsters/BreachBosses/BreachBossPhysical": "Uul-Netol, Unburdened Flesh",
    "Metadata/Monsters/BreachBosses/BreachBossChaos": "Chayula, Who Dreamt",
    "Metadata/Monsters/Breach/WildBreachBoss": "Xesht-Ula, the Open Hand",

    # ── Betrayal syndicate ────────────────────────────────────────────
    "Metadata/Monsters/LeagueBetrayal/BetrayalCatarina": "Catarina, Master of Undeath",
    "Metadata/Monsters/LeagueBetrayal/BetrayalCatarinaMapBoss": "Catarina, Master of Undeath",
    "Metadata/Monsters/LeagueBetrayal/BetrayalCatarina1": "Catarina, Master of Undeath",
    "Metadata/Monsters/LeagueBetrayal/BetrayalCatarina2": "Catarina, Master of Undeath",
    "Metadata/Monsters/LeagueBetrayal/BetrayalAisling": "Aisling Laffrey",
    "Metadata/Monsters/LeagueBetrayal/BetrayalCameria": "Cameria the Coldblooded",
    "Metadata/Monsters/LeagueBetrayal/BetrayalElreon": "Elreon, Light's Judge",
    "Metadata/Monsters/LeagueBetrayal/BetrayalGravicius": "Gravicius Reborn",
    "Metadata/Monsters/LeagueBetrayal/BetrayalGuff": "Guff 'Tiny' Grenn",
    "Metadata/Monsters/LeagueBetrayal/BetrayalHaku": "Haku, Warmaster",
    "Metadata/Monsters/LeagueBetrayal/BetrayalHillock": "Hillock, the Blacksmith",
    "Metadata/Monsters/LeagueBetrayal/BetrayalItThatFled": "It That Fled",
    "Metadata/Monsters/LeagueBetrayal/BetrayalIt": "It That Fled",
    "Metadata/Monsters/LeagueBetrayal/BetrayalJanus": "Janus Perandus",
    "Metadata/Monsters/LeagueBetrayal/BetrayalJorgin": "Jorgin, Necromancer",
    "Metadata/Monsters/LeagueBetrayal/BetrayalKorell": "Korell Goya, Son of Stone",
    "Metadata/Monsters/LeagueBetrayal/BetrayalLeo": "Leo, Wolf of the Pits",
    "Metadata/Monsters/LeagueBetrayal/BetrayalRiker": "Riker Maloney",
    "Metadata/Monsters/LeagueBetrayal/BetrayalRin": "Rin Yuushu, Cartographer",
    "Metadata/Monsters/LeagueBetrayal/BetrayalTora": "Tora, the Culler",
    "Metadata/Monsters/LeagueBetrayal/BetrayalVagan": "Vagan, Victory's Herald",
    "Metadata/Monsters/LeagueBetrayal/BetrayalVorici": "Vorici, Silent Brother",

    # ── Beyond demons (3.19+ Hellscape) ───────────────────────────────
    "Metadata/Monsters/LeagueHellscape/DemonFaction/HellscapeDemonBoss": "K'tash, the Hate Shepherd",
    "Metadata/Monsters/LeagueHellscape/FleshFaction/HellscapeFleshBoss": "Ghorr, the Grasping Maw",
    "Metadata/Monsters/LeagueHellscape/PaleFaction/HellscapePaleBoss": "Beidat, Archangel of Death",

    # ── Beyond demons (legacy) ────────────────────────────────────────
    "Metadata/Monsters/BeyondDemons/BeyondDemon1": "Na'em, Bending Stone",
    "Metadata/Monsters/BeyondDemons/BeyondDemon2": "Haast, Unrelenting Frost",
    "Metadata/Monsters/BeyondDemons/BeyondDemon3": "Bameth, Shifting Darkness",
    "Metadata/Monsters/BeyondDemons/BeyondDemon4": "Tzteosh, Hungering Flame",
    "Metadata/Monsters/BeyondDemons/BeyondDemon5": "Ephij, Crackling Sky",
    "Metadata/Monsters/BeyondDemons/BeyondDemonBoss": "Abaxoth, the End of All That Is",
    "Metadata/Monsters/LeagueBeyond/BeyondDemonBoss1": "Bameth, Shifting Darkness",
    "Metadata/Monsters/LeagueBeyond/BeyondDemonBoss2": "Haast, Unrelenting Frost",
    "Metadata/Monsters/LeagueBeyond/BeyondDemonBoss3": "Ephij, Crackling Sky",
    "Metadata/Monsters/LeagueBeyond/BeyondDemonBoss4": "Tzteosh, Hungering Flame",
    "Metadata/Monsters/LeagueBeyond/BeyondDemonUberBoss": "Abaxoth, the End of All That Is",

    # ── Delirium bosses ───────────────────────────────────────────────
    "Metadata/Monsters/LeagueAffliction/DoodadDaemon/AfflictionBossCold": "Omniphobia, Fear Manifest",
    "Metadata/Monsters/LeagueAffliction/DoodadDaemon/AfflictionBossFire": "Kosis, the Revelation",
    "Metadata/Monsters/LeagueDelirium/DeliriumBoss1": "Omniphobia, Fear Manifest",
    "Metadata/Monsters/LeagueDelirium/DeliriumBoss2": "Kosis, the Revelation",

    # ── Expedition ────────────────────────────────────────────────────
    "Metadata/Monsters/LeagueExpedition/Olroth/OlrothBoss": "Olroth, Origin of the Fall",
    "Metadata/Monsters/LeagueExpedition/Medved/MedvedBoss": "Medved, Feller of Heroes",
    "Metadata/Monsters/LeagueExpedition/BlackScythe/BlackScytheBoss": "Uhtred, Covetous Traitor",
    "Metadata/Monsters/LeagueExpedition/Bear/ExpeditionBear1": "Olroth, Origin of the Fall",
    "Metadata/Monsters/LeagueExpedition/Bear/ExpeditionBear2": "Medved, Feller of Heroes",
    "Metadata/Monsters/LeagueExpedition/Bear/ExpeditionBear3": "Uhtred, Covetous Traitor",
    "Metadata/Monsters/LeagueExpedition/Bear/ExpeditionBear4": "Vorana, Last to Fall",

    # ── Essence ───────────────────────────────────────────────────────
    "Metadata/Monsters/LeagueEssence/EssenceMonsterCorrupted1": "Essence of Hysteria",
    "Metadata/Monsters/LeagueEssence/EssenceMonsterCorrupted2": "Essence of Insanity",
    "Metadata/Monsters/LeagueEssence/EssenceMonsterCorrupted3": "Essence of Horror",
    "Metadata/Monsters/LeagueEssence/EssenceMonsterCorrupted4": "Essence of Delirium",

    # ── Bestiary ──────────────────────────────────────────────────────
    "Metadata/Monsters/LeagueBestiary/Spider/BestiarySpiritBeastBoss": "Farrul, First of the Plains",
    "Metadata/Monsters/LeagueBestiary/Crab/BestiarySpiritBeastBoss": "Craiceann, First of the Deep",
    "Metadata/Monsters/LeagueBestiary/Ape/BestiarySpiritBeastBoss": "Fenumus, First of the Night",
    "Metadata/Monsters/LeagueBestiary/Snake/BestiarySpiritBeastBoss": "Saqawal, First of the Sky",

    # ── Legion ────────────────────────────────────────────────────────
    "Metadata/Monsters/LeagueLegion/LegionKaruiGeneral": "Amanamu, Liege of the Lightless",
    "Metadata/Monsters/LeagueLegion/LegionEternalEmpireGeneral": "General of the Eternal Empire",
    "Metadata/Monsters/LeagueLegion/LegionMarakethGeneral": "Aukuna, the Black Sekhema",
    "Metadata/Monsters/LeagueLegion/LegionTemplarGeneral": "Venarius, the Eternal Scholar",
    "Metadata/Monsters/LeagueLegion/LegionVaalGeneral": "Vaal General",

    # ── Blight ────────────────────────────────────────────────────────
    "Metadata/Monsters/LeagueBlight/BlightBossPhysical": "Blight Boss (Physical)",
    "Metadata/Monsters/LeagueBlight/BlightBossFire": "Blight Boss (Fire)",
    "Metadata/Monsters/LeagueBlight/BlightBossCold": "Blight Boss (Cold)",
    "Metadata/Monsters/LeagueBlight/BlightBossLightning": "Blight Boss (Lightning)",
    "Metadata/Monsters/LeagueBlight/BlightBossChaos": "Blight Boss (Chaos)",

    # ── Metamorph / Ritual / Scourge ──────────────────────────────────
    "Metadata/Monsters/LeagueMetamorph/MetamorphBoss": "Metamorph",
    "Metadata/Monsters/LeagueRitual/RitualDaemonFire": "Ritual (Fire)",
    "Metadata/Monsters/LeagueRitual/RitualDaemonCold": "Ritual (Cold)",
    "Metadata/Monsters/LeagueRitual/RitualDaemonLightning": "Ritual (Lightning)",
    "Metadata/Monsters/LeagueRitual/RitualDaemonPhysical": "Ritual (Physical)",
    "Metadata/Monsters/LeagueHellscape/HellscapeKrangBoss": "The Scourge",

    # ── Rogue Exiles ──────────────────────────────────────────────────
    "Metadata/Monsters/Exiles/ExileDuelist1": "Jonah, Sahkav's Fortune",
    "Metadata/Monsters/Exiles/ExileDuelist2": "Torr Olgosso",
    "Metadata/Monsters/Exiles/ExileDuelist3": "Ailentia Rac",
    "Metadata/Monsters/Exiles/ExileMarauder1": "Igna Phoenix",
    "Metadata/Monsters/Exiles/ExileMarauder2": "Magnus Stonethorn",
    "Metadata/Monsters/Exiles/ExileRanger1": "Orra Greengate",
    "Metadata/Monsters/Exiles/ExileRanger2": "Antalie Napora",
    "Metadata/Monsters/Exiles/ExileScion1": "Kirmes, the Undying",
    "Metadata/Monsters/Exiles/ExileShadow1": "Ion Darkshroud",
    "Metadata/Monsters/Exiles/ExileShadow2": "Ash Lessard",
    "Metadata/Monsters/Exiles/ExileShadow3": "Vickas Giantbone",
    "Metadata/Monsters/Exiles/ExileTemplar1": "Eoin Greyfur",
    "Metadata/Monsters/Exiles/ExileTemplar2": "Wilorin Demontamer",
    "Metadata/Monsters/Exiles/ExileWitch1": "Minara Anemina",
    "Metadata/Monsters/Exiles/ExileWitch2": "Augustina Solaria",
    "Metadata/Monsters/Exiles/Titucius": "Titucius, the Wretched",

    # ── Campaign bosses ───────────────────────────────────────────────
    "Metadata/Monsters/Brutus/Brutus": "Brutus, Lord Incarcerator",
    "Metadata/Monsters/Merveil/Merveil": "Merveil, the Siren",
    "Metadata/Monsters/Fidelitas/Fidelitas": "Fidelitas, the Mourning",
    "Metadata/Monsters/VaalOversoul/VaalOversoul": "Vaal Oversoul",
    "Metadata/Monsters/Piety/Piety": "Piety the Empyrean",
    "Metadata/Monsters/Dominus/Dominus": "Dominus, High Templar",
    "Metadata/Monsters/Daresso/Daresso": "Daresso, King of Swords",
    "Metadata/Monsters/Daresso/DaressoBoss": "Daresso, King of Swords",
    "Metadata/Monsters/KaomBoss/KaomBoss": "Kaom, the Sovereign",
    "Metadata/Monsters/Malachai/Malachai": "Malachai, the Nightmare",
    "Metadata/Monsters/Kitava/Kitava": "Kitava, the Insatiable",
    "Metadata/Monsters/Kitava/KitavaBoss": "Kitava, the Insatiable",
    "Metadata/Monsters/Kitava/KitavaFinal": "Kitava, the Insatiable",
    "Metadata/Monsters/Avarius/Avarius": "High Templar Avarius",
    "Metadata/Monsters/Innocence/Innocence": "Innocence, God-Emperor's Justice",
    "Metadata/Monsters/Doedre/Doedre": "Doedre Darktongue",
    "Metadata/Monsters/BrineKing/BrineKing": "Tsoagoth, the Brine King",
    "Metadata/Monsters/Abberath/Abberath": "Abberath",

    # ── Labyrinth ─────────────────────────────────────────────────────
    "Metadata/Monsters/Izaro/Izaro": "Izaro",
    "Metadata/Monsters/Izaro/IzaroUber": "Izaro (Uber Lab)",
    "Metadata/Monsters/Labyrinth/LabyrinthTrap": "Lab Trap",

    # ── Map bosses ────────────────────────────────────────────────────
    "Metadata/Monsters/Axis/MapPietyBoss": "Piety the Empyrean",
    "Metadata/Monsters/Shavronne/ShavronneMapBoss": "Shavronne of Umbra",
    "Metadata/Monsters/Cannibal/HailrakeMapBoss": "Hailrake",
    "Metadata/Monsters/BanditLeaderKraityn/BanditLeaderKraitynMapBoss": "Kraityn, Scarbearer",
    "Metadata/Monsters/BanditLeaderAlira/BanditLeaderAliraMapBoss": "Alira Darktongue",
    "Metadata/Monsters/BanditLeaderOak/BanditLeaderOakMapBoss": "Oak, Skullbreaker",

    # ── Abyss ─────────────────────────────────────────────────────────
    "Metadata/Monsters/LeagueAbyss/AbyssFlayerBoss": "Abyss Lich",
    "Metadata/Monsters/LeagueAbyss/AbyssBat": "Stygian Revenant",
}


# Primary damage element for known monsters.
# Used to show "Killed by X (Fire)" even though PoE's log doesn't include damage type.
MONSTER_ELEMENTS: dict[str, str] = {
    # ── Ground effects & on-death ────────────────────────────────────
    "Metadata/Monsters/InvisibleFire/InvisibleChaosstorm": "Chaos",
    "Metadata/Monsters/InvisibleFire/InvisibleChaostorm": "Chaos",
    "Metadata/Monsters/InvisibleFire/InvisibleFireAfterDeath": "Fire",
    "Metadata/Monsters/InvisibleFire/AfterDeathFireDegen": "Fire",
    "Metadata/Monsters/InvisibleFire/AfterDeathColdDegen": "Cold",
    "Metadata/Monsters/InvisibleFire/AfterDeathChaosDegen": "Chaos",
    "Metadata/Monsters/InvisibleFire/InvisibleFireDegen": "Fire",
    "Metadata/Monsters/InvisibleFire/InvisibleCausticGround": "Chaos",
    "Metadata/Monsters/InvisibleFire/InvisibleChilledGround": "Cold",
    "Metadata/Monsters/InvisibleFire/InvisibleShockedGround": "Lightning",
    "Metadata/Monsters/InvisibleFire/InvisibleDesecrate": "Chaos",
    "Metadata/Monsters/InvisibleFire/InvisibleProfaneGround": "Chaos",
    "Metadata/Monsters/InvisibleFire/InvisibleTarGround": "Physical",
    "Metadata/Monsters/InvisibleFire/InvisibleSandstorm": "Physical",
    "Metadata/Monsters/InvisibleFire/InvisibleFireRighteousFire": "Fire",
    "Metadata/Monsters/InvisibleFire/InvisibleFireRighteousFireMetamorphosis": "Fire",
    "Metadata/Monsters/InvisibleFire/InvisibleFireStormcallMapBoss": "Lightning",
    "Metadata/Monsters/InvisibleFire/InvisibleFireColdSnapMap": "Cold",
    "Metadata/Monsters/InvisibleFire/InvisibleFireAfflictionDemonColdDegen": "Cold",
    "Metadata/Monsters/InvisibleFire/InvisibleFireAfflictionDemonFireDegen": "Fire",
    "Metadata/Monsters/InvisibleFire/InvisibleFrostboltDegen": "Cold",
    "Metadata/Monsters/InvisibleFire/InvisibleFireMortarDegen": "Fire",

    # ── Bearers ──────────────────────────────────────────────────────
    "Metadata/Monsters/Daemon/BearerOfTheGuardian": "Physical",
    "Metadata/Monsters/Daemon/BearerOfTorment": "Chaos",
    "Metadata/Monsters/Daemon/BearerOfBlessing": "Lightning",
    "Metadata/Monsters/Daemon/BearerOfFragility": "Physical",
    "Metadata/Monsters/Daemon/DaemonBearerOfFlame": "Fire",
    "Metadata/Monsters/Daemon/DaemonBearerOfFrost": "Cold",
    "Metadata/Monsters/Daemon/DaemonBearerOfLightning": "Lightning",
    "Metadata/Monsters/Daemon/DaemonBearerOfBlood": "Physical",
    "Metadata/Monsters/Daemon/DaemonBearerOfGuardians": "Physical",

    # ── Volatiles ────────────────────────────────────────────────────
    "Metadata/Monsters/Daemon/VolatileCoreFire": "Fire",
    "Metadata/Monsters/Daemon/VolatileCoreCold": "Cold",
    "Metadata/Monsters/Daemon/VolatileCoreLightning": "Lightning",
    "Metadata/Monsters/Daemon/VolatileCorePhysical": "Physical",
    "Metadata/Monsters/Daemon/VolatileCoreChaos": "Chaos",
    "Metadata/Monsters/VolatileCore/VolatileCore": "Fire",
    "Metadata/Monsters/VolatileCore/VolatileDeadCore": "Fire",

    # ── Boss damage daemons ──────────────────────────────────────────
    "Metadata/Monsters/Daemon/DaemonShaperBeam": "Cold",
    "Metadata/Monsters/Daemon/DaemonShaperBall": "Cold",
    "Metadata/Monsters/Daemon/DaemonSirusMeteor": "Physical",
    "Metadata/Monsters/Daemon/DaemonMaven": "Fire",
    "Metadata/Monsters/Daemon/DaemonElderShockNova": "Lightning",
    "Metadata/Monsters/Daemon/MoltenShellDaemon": "Fire",
    "Metadata/Monsters/Daemon/DaemonLabyrinthTrap": "Physical",
    "Metadata/Monsters/Daemon/BreachBossFire": "Fire",

    # ── Endgame bosses ───────────────────────────────────────────────
    "Metadata/Monsters/AtlasBosses/TheShaperBoss": "Cold",
    "Metadata/Monsters/AtlasBosses/TheShaperBossUberElder": "Cold",
    "Metadata/Monsters/AtlasBosses/TheElder": "Physical",
    "Metadata/Monsters/AtlasBosses/TheElderBoss": "Physical",
    "Metadata/Monsters/AtlasBosses/TheElderBossEscaped": "Physical",
    "Metadata/Monsters/AtlasBosses/TheElderUber": "Physical",
    "Metadata/Monsters/AtlasExiles/AtlasExile1": "Chaos",       # Al-Hezmin
    "Metadata/Monsters/AtlasExiles/AtlasExile2": "Cold",        # Veritania
    "Metadata/Monsters/AtlasExiles/AtlasExile3": "Physical",    # Drox
    "Metadata/Monsters/AtlasExiles/AtlasExile4": "Lightning",   # Baran
    "Metadata/Monsters/AtlasExiles/AtlasExile5": "Physical",    # Sirus
    "Metadata/Monsters/AtlasExiles/AtlasExile5Throne": "Physical",
    "Metadata/Monsters/AtlasExiles/AtlasExile1Uber": "Chaos",
    "Metadata/Monsters/AtlasExiles/AtlasExile2Uber": "Cold",
    "Metadata/Monsters/AtlasExiles/AtlasExile3Uber": "Physical",
    "Metadata/Monsters/AtlasExiles/AtlasExile4Uber": "Lightning",
    "Metadata/Monsters/AtlasExiles/AtlasExile5Uber": "Physical",
    "Metadata/Monsters/MavenBoss/TheMaven": "Fire",
    "Metadata/Monsters/MavenBoss/TheMavenEnraged": "Fire",
    "Metadata/Monsters/AtlasInvaders/CleansingBoss": "Fire",    # Searing Exarch
    "Metadata/Monsters/AtlasInvaders/ConsumeBoss": "Physical",  # Eater of Worlds
    "Metadata/Monsters/AtlasInvaders/BlackStarBoss": "Cold",
    "Metadata/Monsters/AtlasInvaders/DoomBoss": "Chaos",        # Infinite Hunger
    "Metadata/Monsters/AtlasBosses/SearingExarch": "Fire",
    "Metadata/Monsters/AtlasBosses/EaterOfWorlds": "Physical",
    "Metadata/Monsters/AtlasBosses/TheBlackStar": "Cold",
    "Metadata/Monsters/AtlasBosses/TheInfiniteHunger": "Chaos",

    # ── Shaper guardians ─────────────────────────────────────────────
    "Metadata/Monsters/AtlasBosses/ShaperGuardianPhoenix": "Fire",
    "Metadata/Monsters/AtlasBosses/ShaperGuardianMinotaur": "Lightning",
    "Metadata/Monsters/AtlasBosses/ShaperGuardianChimera": "Physical",
    "Metadata/Monsters/AtlasBosses/ShaperGuardianHydra": "Cold",
    "Metadata/Monsters/AtlasBosses/PhoenixBoss": "Fire",
    "Metadata/Monsters/AtlasBosses/MinotaurBoss": "Lightning",
    "Metadata/Monsters/AtlasBosses/ChimeraBoss": "Physical",
    "Metadata/Monsters/AtlasBosses/HydraBoss": "Cold",

    # ── Elder guardians ──────────────────────────────────────────────
    "Metadata/Monsters/AtlasBosses/ElderGuardianPurifier": "Fire",
    "Metadata/Monsters/AtlasBosses/ElderGuardianConstrictor": "Chaos",
    "Metadata/Monsters/AtlasBosses/ElderGuardianEnslaverBoss": "Physical",
    "Metadata/Monsters/AtlasBosses/ElderGuardianEradicator": "Lightning",

    # ── Atziri ───────────────────────────────────────────────────────
    "Metadata/Monsters/Atziri/Atziri": "Fire",
    "Metadata/Monsters/Atziri/Atziri2": "Fire",
    "Metadata/Monsters/Atziri/AtziriUber": "Fire",

    # ── Breach bosses ────────────────────────────────────────────────
    "Metadata/Monsters/BreachBosses/BreachBossFireMap": "Fire",
    "Metadata/Monsters/BreachBosses/BreachBossColdMap": "Cold",
    "Metadata/Monsters/BreachBosses/BreachBossLightningMap": "Lightning",
    "Metadata/Monsters/BreachBosses/BreachBossPhysicalMap": "Physical",
    "Metadata/Monsters/BreachBosses/BreachBossChaosMap": "Chaos",
    "Metadata/Monsters/BreachBosses/BreachBossFire": "Fire",
    "Metadata/Monsters/BreachBosses/BreachBossCold": "Cold",
    "Metadata/Monsters/BreachBosses/BreachBossLightning": "Lightning",
    "Metadata/Monsters/BreachBosses/BreachBossPhysical": "Physical",
    "Metadata/Monsters/BreachBosses/BreachBossChaos": "Chaos",
    "Metadata/Monsters/Breach/WildBreachBoss": "Physical",

    # ── Betrayal ─────────────────────────────────────────────────────
    "Metadata/Monsters/LeagueBetrayal/BetrayalCatarina": "Chaos",
    "Metadata/Monsters/LeagueBetrayal/BetrayalCatarinaMapBoss": "Chaos",
    "Metadata/Monsters/LeagueBetrayal/BetrayalCatarina1": "Chaos",
    "Metadata/Monsters/LeagueBetrayal/BetrayalCatarina2": "Chaos",

    # ── Beyond demons ────────────────────────────────────────────────
    "Metadata/Monsters/BeyondDemons/BeyondDemon1": "Physical",    # Na'em
    "Metadata/Monsters/BeyondDemons/BeyondDemon2": "Cold",        # Haast
    "Metadata/Monsters/BeyondDemons/BeyondDemon3": "Chaos",       # Bameth
    "Metadata/Monsters/BeyondDemons/BeyondDemon4": "Fire",        # Tzteosh
    "Metadata/Monsters/BeyondDemons/BeyondDemon5": "Lightning",   # Ephij
    "Metadata/Monsters/BeyondDemons/BeyondDemonBoss": "Chaos",    # Abaxoth
    "Metadata/Monsters/LeagueBeyond/BeyondDemonBoss1": "Chaos",
    "Metadata/Monsters/LeagueBeyond/BeyondDemonBoss2": "Cold",
    "Metadata/Monsters/LeagueBeyond/BeyondDemonBoss3": "Lightning",
    "Metadata/Monsters/LeagueBeyond/BeyondDemonBoss4": "Fire",
    "Metadata/Monsters/LeagueBeyond/BeyondDemonUberBoss": "Chaos",
    "Metadata/Monsters/LeagueHellscape/DemonFaction/HellscapeDemonBoss": "Fire",
    "Metadata/Monsters/LeagueHellscape/FleshFaction/HellscapeFleshBoss": "Physical",
    "Metadata/Monsters/LeagueHellscape/PaleFaction/HellscapePaleBoss": "Cold",

    # ── Delirium ─────────────────────────────────────────────────────
    "Metadata/Monsters/LeagueAffliction/DoodadDaemon/AfflictionBossCold": "Cold",
    "Metadata/Monsters/LeagueAffliction/DoodadDaemon/AfflictionBossFire": "Fire",
    "Metadata/Monsters/LeagueDelirium/DeliriumBoss1": "Cold",
    "Metadata/Monsters/LeagueDelirium/DeliriumBoss2": "Fire",

    # ── Blight ───────────────────────────────────────────────────────
    "Metadata/Monsters/LeagueBlight/BlightBossPhysical": "Physical",
    "Metadata/Monsters/LeagueBlight/BlightBossFire": "Fire",
    "Metadata/Monsters/LeagueBlight/BlightBossCold": "Cold",
    "Metadata/Monsters/LeagueBlight/BlightBossLightning": "Lightning",
    "Metadata/Monsters/LeagueBlight/BlightBossChaos": "Chaos",

    # ── Ritual ───────────────────────────────────────────────────────
    "Metadata/Monsters/LeagueRitual/RitualDaemonFire": "Fire",
    "Metadata/Monsters/LeagueRitual/RitualDaemonCold": "Cold",
    "Metadata/Monsters/LeagueRitual/RitualDaemonLightning": "Lightning",
    "Metadata/Monsters/LeagueRitual/RitualDaemonPhysical": "Physical",

    # ── Essence ──────────────────────────────────────────────────────
    "Metadata/Monsters/LeagueEssence/EssenceMonsterCorrupted1": "Fire",
    "Metadata/Monsters/LeagueEssence/EssenceMonsterCorrupted2": "Lightning",
    "Metadata/Monsters/LeagueEssence/EssenceMonsterCorrupted3": "Cold",
    "Metadata/Monsters/LeagueEssence/EssenceMonsterCorrupted4": "Chaos",

    # ── Campaign bosses ──────────────────────────────────────────────
    "Metadata/Monsters/Brutus/Brutus": "Physical",
    "Metadata/Monsters/Merveil/Merveil": "Cold",
    "Metadata/Monsters/Fidelitas/Fidelitas": "Lightning",
    "Metadata/Monsters/VaalOversoul/VaalOversoul": "Physical",
    "Metadata/Monsters/Piety/Piety": "Lightning",
    "Metadata/Monsters/Dominus/Dominus": "Lightning",
    "Metadata/Monsters/Daresso/Daresso": "Physical",
    "Metadata/Monsters/Daresso/DaressoBoss": "Physical",
    "Metadata/Monsters/KaomBoss/KaomBoss": "Fire",
    "Metadata/Monsters/Malachai/Malachai": "Physical",
    "Metadata/Monsters/Kitava/Kitava": "Fire",
    "Metadata/Monsters/Kitava/KitavaBoss": "Fire",
    "Metadata/Monsters/Kitava/KitavaFinal": "Fire",
    "Metadata/Monsters/Avarius/Avarius": "Fire",
    "Metadata/Monsters/Innocence/Innocence": "Fire",
    "Metadata/Monsters/Doedre/Doedre": "Chaos",
    "Metadata/Monsters/BrineKing/BrineKing": "Cold",
    "Metadata/Monsters/Abberath/Abberath": "Fire",

    # ── Labyrinth ────────────────────────────────────────────────────
    "Metadata/Monsters/Izaro/Izaro": "Physical",
    "Metadata/Monsters/Izaro/IzaroUber": "Physical",
    "Metadata/Monsters/Labyrinth/LabyrinthTrap": "Physical",

    # ── Metamorph / Scourge ──────────────────────────────────────────
    "Metadata/Monsters/LeagueMetamorph/MetamorphBoss": "Physical",
    "Metadata/Monsters/LeagueHellscape/HellscapeKrangBoss": "Physical",
}


# Boss zone → primary damage element (fallback when killer is unknown).
BOSS_ZONE_ELEMENTS: dict[str, str] = {
    "The Shaper's Realm": "Cold",
    "Absence of Value and Meaning": "Physical",    # Sirus
    "Eye of the Storm": "Physical",                 # Sirus
    "The Maven's Crucible": "Fire",
    "The Elder's Domain": "Physical",
    "Absence of Symmetry and Harmony": "Physical",  # Uber Elder
    "Searing Exarch Arena": "Fire",
    "The Eater of Worlds' Arena": "Physical",
    "Black Star Arena": "Cold",
    "The Infinite Hunger Arena": "Chaos",
    "Xoph's Domain": "Fire",
    "Tul's Domain": "Cold",
    "Esh's Domain": "Lightning",
    "Uul-Netol's Domain": "Physical",
    "Chayula's Domain": "Chaos",
    "The Cathedral Rooftop": "Fire",       # Kitava
    "The Feeding Trough": "Fire",          # Kitava Act 10
    "The Arbiter of Ash Arena": "Fire",    # PoE 2
}
