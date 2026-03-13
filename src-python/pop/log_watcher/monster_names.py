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
