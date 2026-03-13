/**
 * PoE gem colour classification.
 *
 * Gems are coloured by their primary attribute requirement:
 *   Red   = Strength
 *   Green = Dexterity
 *   Blue  = Intelligence
 *   White = no requirement (e.g. Portal, Detonate Mines, Enlighten)
 *
 * We classify by name lookup for known gems, then fall back to heuristics.
 */

export type GemColor = "red" | "green" | "blue" | "white";

// Strength (Red) gems — melee attacks, warcries, physical/fire skills
const RED_GEMS = new Set([
  // Melee attacks
  "Cyclone", "Lacerate", "Double Strike", "Blade Flurry", "Molten Strike",
  "Flicker Strike", "Boneshatter", "Frost Blades", "Elemental Hit", "Wild Strike",
  "Smite", "Reave", "Viper Strike", "Puncture", "Cleave", "Ground Slam",
  "Earthquake", "Sunder", "Tectonic Slam", "Consecrated Path", "Glacial Hammer",
  "Ice Crash", "Infernal Blow", "Heavy Strike", "Dominating Blow", "Static Strike",
  "Ancestral Protector", "Ancestral Warchief", "Vaal Ancestral Warchief",
  "Shield Charge", "Leap Slam", "Vigilant Strike", "Perforate", "Lancing Steel",
  "Shattering Steel", "Splitting Steel", "Rage Vortex", "Earthshatter",
  "Bladestorm", "Chain Hook",
  // Fire/Str spells
  "Molten Shell", "Immortal Call", "Enduring Cry", "Intimidating Cry",
  "Seismic Cry", "Rallying Cry", "Infernal Cry", "Generals Cry", "General's Cry",
  "Determination", "Vitality", "Anger", "Purity of Fire", "Herald of Ash",
  "Berserk", "Blood and Sand", "Flesh and Stone",
  // Str supports
  "Melee Physical Damage Support", "Multistrike Support", "Ruthless Support",
  "Fortify Support", "Pulverise Support", "Rage Support", "Fist of War Support",
  "Impale Support", "Brutality Support", "Bloodlust Support", "Close Combat Support",
  "Shockwave Support", "Ancestral Call Support", "Maim Support",
  "Chance to Bleed Support", "Lifetap Support", "Intimidate Support",
  "Combustion Support", "Burning Damage Support", "Fire Penetration Support",
  "Immolate Support", "Infernal Legion Support", "Elemental Damage with Attacks Support",
  "Added Fire Damage Support",
  "Awakened Melee Physical Damage Support", "Awakened Multistrike Support",
  "Awakened Brutality Support", "Awakened Burning Damage Support",
  "Awakened Fire Penetration Support", "Awakened Elemental Damage with Attacks Support",
  "Awakened Added Fire Damage Support",
  // Vaal
  "Vaal Molten Shell", "Vaal Cyclone", "Vaal Double Strike", "Vaal Earthquake",
  "Vaal Ground Slam", "Vaal Immortal Call", "Vaal Flicker Strike",
]);

// Dexterity (Green) gems — ranged attacks, evasion, cold/phys
const GREEN_GEMS = new Set([
  // Bow attacks
  "Rain of Arrows", "Tornado Shot", "Lightning Arrow", "Ice Shot", "Burning Arrow",
  "Caustic Arrow", "Toxic Rain", "Barrage", "Split Arrow", "Shrapnel Shot",
  "Galvanic Arrow", "Artillery Ballista", "Shrapnel Ballista", "Siege Ballista",
  "Blast Rain", "Mirror Arrow", "Blink Arrow", "Scourge Arrow", "Ensnaring Arrow",
  "Vaal Rain of Arrows", "Vaal Burning Arrow", "Vaal Lightning Arrow",
  // Dex melee
  "Cobra Lash", "Pestilent Strike", "Spectral Throw", "Whirling Blades",
  "Blade Trap", "Ethereal Knives",
  // Dex utility
  "Grace", "Haste", "Herald of Ice", "Phase Run", "Dash", "Smoke Mine",
  "Withering Step", "Blood Rage", "Poacher's Mark",
  "Arrow Nova Support",
  // Dex supports
  "Added Cold Damage Support", "Mirage Archer Support", "Greater Multiple Projectiles Support",
  "Lesser Multiple Projectiles Support", "Chain Support", "Fork Support",
  "Pierce Support", "Volley Support", "Barrage Support", "Ballista Totem Support",
  "Vicious Projectiles Support", "Swift Affliction Support", "Deadly Ailments Support",
  "Unbound Ailments Support", "Void Manipulation Support", "Withering Touch Support",
  "Nightblade Support", "Faster Attacks Support", "Increased Critical Strikes Support",
  "Increased Critical Damage Support", "Trap Support", "Cluster Traps Support",
  "Multiple Traps Support", "Trap and Mine Damage Support", "Advanced Traps Support",
  "Point Blank Support", "Vile Toxins Support", "Faster Projectiles Support",
  "Slower Projectiles Support", "Cold Penetration Support", "Hypothermia Support",
  "Ice Bite Support", "Inspiration Support", "Momentum Support",
  "Focused Ballista Support",
  "Awakened Added Cold Damage Support", "Awakened Greater Multiple Projectiles Support",
  "Awakened Chain Support", "Awakened Vicious Projectiles Support",
  "Awakened Swift Affliction Support", "Awakened Deadly Ailments Support",
  "Awakened Void Manipulation Support", "Awakened Cold Penetration Support",
  "Awakened Fork Support",
]);

// Intelligence (Blue) gems — spells, curses, auras, minions
const BLUE_GEMS = new Set([
  // Spells
  "Fireball", "Firestorm", "Flame Surge", "Incinerate", "Flameblast",
  "Rolling Magma", "Cremation", "Blazing Salvo",
  "Arc", "Ball Lightning", "Storm Brand", "Orb of Storms", "Spark",
  "Lightning Tendrils", "Shock Nova", "Crackling Lance", "Galvanic Field",
  "Ice Nova", "Freezing Pulse", "Frostbolt", "Winter Orb", "Cold Snap",
  "Arctic Breath", "Glacial Cascade", "Creeping Frost", "Vortex", "Frost Bomb",
  "Essence Drain", "Contagion", "Bane", "Soulrend", "Dark Pact",
  "Forbidden Rite", "Hexblast",
  // Minion
  "Raise Zombie", "Summon Skeleton", "Summon Raging Spirit", "Raise Spectre",
  "Summon Holy Relic", "Animate Guardian", "Absolution", "Summon Carrion Golem",
  "Summon Stone Golem", "Summon Chaos Golem", "Summon Flame Golem",
  "Summon Ice Golem", "Summon Lightning Golem",
  // Auras/Curses
  "Clarity", "Discipline", "Zealotry", "Wrath", "Hatred", "Malevolence",
  "Purity of Elements", "Purity of Ice", "Purity of Lightning",
  "Herald of Thunder", "Herald of Purity", "Tempest Shield",
  "Conductivity", "Frostbite", "Flammability", "Elemental Weakness",
  "Despair", "Enfeeble", "Temporal Chains", "Punishment", "Vulnerability",
  "Assassin's Mark", "Sniper's Mark", "Warlord's Mark",
  "Arcanist Brand", "Storm Call",
  // Blue supports
  "Spell Echo Support", "Controlled Destruction Support", "Elemental Focus Support",
  "Concentrated Effect Support", "Increased Area of Effect Support",
  "Awakened Controlled Destruction Support", "Awakened Elemental Focus Support",
  "Awakened Concentrated Effect Support", "Awakened Increased Area of Effect Support",
  "Added Lightning Damage Support", "Lightning Penetration Support",
  "Awakened Added Lightning Damage Support", "Awakened Lightning Penetration Support",
  "Power Charge on Critical Support", "Arcane Surge Support", "Spell Cascade Support",
  "Unleash Support", "Intensify Support", "Pinpoint Support",
  "Minion Damage Support", "Minion Speed Support", "Feeding Frenzy Support",
  "Predator Support", "Meat Shield Support", "Empower Support",
  "Awakened Minion Damage Support",
  "Hextouch Support", "Blasphemy Support", "Curse on Hit Support",
  "Enlighten Support", "Enhance Support",
  "Cast when Damage Taken Support", "Cast on Critical Strike Support",
  "Faster Casting Support", "Efficacy Support", "Energy Leech Support",
  // DoT supports
  "Decay Support",
  // Vaal
  "Vaal Arc", "Vaal Fireball", "Vaal Spark", "Vaal Ice Nova",
  "Vaal Cold Snap", "Vaal Discipline", "Vaal Clarity", "Vaal Grace", "Vaal Haste",
]);

/** Determine gem colour from name. */
export function getGemColor(name: string): GemColor {
  // Try exact name, then with " Support" appended (PoB strips "Support" from names)
  const variants = [name, name + " Support"];
  for (const v of variants) {
    if (RED_GEMS.has(v)) return "red";
    if (GREEN_GEMS.has(v)) return "green";
    if (BLUE_GEMS.has(v)) return "blue";
  }
  // Also try without " Support" suffix
  const stripped = name.replace(/ Support$/, "");
  if (stripped !== name) {
    if (RED_GEMS.has(stripped)) return "red";
    if (GREEN_GEMS.has(stripped)) return "green";
    if (BLUE_GEMS.has(stripped)) return "blue";
  }

  // Heuristic fallback based on common keywords
  const lower = name.toLowerCase();

  // Red (Str) — must check BEFORE blue/green to avoid false matches
  if (lower.includes("melee") || lower.includes("fortify") || lower.includes("brutality")
    || lower.includes("impale") || lower.includes("maim")
    || lower.includes("burning") || lower.includes("combustion") || lower.includes("immolate")
    || lower.includes("lifetap") || lower.includes("bloodlust")
    || lower.includes("rage") || lower.includes("pulverise")
    || lower.includes("multistrike") || lower.includes("ruthless")
    || lower.includes("shockwave support") || lower.includes("close combat")
    || lower.includes("elemental damage with attacks") || lower.includes("added fire")
    || lower.includes("chance to bleed") || lower.includes("intimidat")
    || lower.includes("infernal") || lower.includes("ancestral call")
    || lower.includes("fire penetration")) return "red";

  // Green (Dex)
  if (lower.includes("projectile") || lower.includes("arrow") || lower.includes("mirage")
    || lower.includes("ballista") || lower.includes("trap") || lower.includes("mine")
    || lower.includes("cold damage") || lower.includes("cold penetration")
    || lower.includes("ice bite") || lower.includes("hypothermia")
    || lower.includes("vicious") || lower.includes("nightblade") || lower.includes("faster attack")
    || lower.includes("critical strike") || lower.includes("critical damage")
    || lower.includes("momentum") || lower.includes("pierce")
    || lower.includes("chain support") || lower.includes("fork")
    || lower.includes("volley") || lower.includes("inspiration")
    || lower.includes("manaforged") || lower.includes("swift affliction")
    || lower.includes("deadly ailment") || lower.includes("unbound ailment")
    || lower.includes("void manipulation") || lower.includes("withering touch")
    || lower.includes("point blank") || lower.includes("vile toxin")
    || lower.includes("focused ballista")) return "green";

  // Blue (Int)
  if (lower.includes("spell") || lower.includes("minion") || lower.includes("curse")
    || lower.includes("lightning damage") || lower.includes("lightning penetration")
    || lower.includes("controlled destruction") || lower.includes("elemental focus")
    || lower.includes("concentrated effect") || lower.includes("area of effect")
    || lower.includes("echo") || lower.includes("unleash") || lower.includes("arcane surge")
    || lower.includes("cast when") || lower.includes("cast on")
    || lower.includes("efficacy") || lower.includes("empower")
    || lower.includes("enhance") || lower.includes("enlighten")
    || lower.includes("hextouch") || lower.includes("blasphemy")
    || lower.includes("power charge") || lower.includes("energy leech")
    || lower.includes("pinpoint") || lower.includes("intensify")
    || lower.includes("feeding frenzy") || lower.includes("predator")
    || lower.includes("meat shield") || lower.includes("decay")
    || lower.includes("volatility") || lower.includes("faster casting")) return "blue";

  // Active gem heuristics
  if (lower.includes("slam") || lower.includes("cry") || lower.includes("warchief")) return "red";
  if (lower.includes("strike") && !lower.includes("lightning")) return "red";
  if (lower.includes("shot") || lower.includes("barrage") || lower.includes("rain")
    || lower.includes("tornado") || lower.includes("frenzy")
    || lower.includes("frostblink") || lower.includes("ensnaring")) return "green";
  if (lower.includes("bolt") || lower.includes("brand")
    || lower.includes("summon") || lower.includes("raise")
    || lower.includes("golem") || lower.includes("mark")) return "blue";
  if (lower.includes("nova")) return "blue";
  if (lower.includes("anger") || lower.includes("determination") || lower.includes("vitality")) return "red";
  if (lower.includes("grace") || lower.includes("haste") || lower.includes("herald of ice")) return "green";
  if (lower.includes("herald") || lower.includes("wrath") || lower.includes("hatred")
    || lower.includes("clarity") || lower.includes("discipline") || lower.includes("zealotry")
    || lower.includes("malevolence") || lower.includes("precision")
    || lower.includes("purity")) return "blue";

  // Default: white
  return "white";
}

/** Build a poewiki icon URL for a gem. Tries with "Support" suffix for support gems. */
export function gemIconUrl(name: string, isSupport?: boolean): string {
  const slug = name.replace(/ /g, "_");
  // PoE wiki uses full name with "Support" suffix for support gems
  if (isSupport && !name.includes("Support")) {
    return `https://www.poewiki.net/wiki/Special:FilePath/${slug}_Support_inventory_icon.png`;
  }
  return `https://www.poewiki.net/wiki/Special:FilePath/${slug}_inventory_icon.png`;
}
