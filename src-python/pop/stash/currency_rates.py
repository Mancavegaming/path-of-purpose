"""Fetch currency-to-chaos exchange rates from poe.ninja."""

from __future__ import annotations

import httpx

# Fallback rates if poe.ninja is unavailable (approximate, updated periodically)
FALLBACK_RATES: dict[str, float] = {
    "Chaos Orb": 1.0,
    "Divine Orb": 180.0,
    "Exalted Orb": 8.0,
    "Orb of Annulment": 12.0,
    "Orb of Alchemy": 0.1,
    "Orb of Alteration": 0.06,
    "Orb of Fusing": 0.2,
    "Jeweller's Orb": 0.08,
    "Chromatic Orb": 0.05,
    "Orb of Scouring": 0.3,
    "Orb of Chance": 0.05,
    "Orb of Regret": 0.5,
    "Regal Orb": 0.5,
    "Vaal Orb": 0.8,
    "Gemcutter's Prism": 1.0,
    "Glassblower's Bauble": 0.03,
    "Cartographer's Chisel": 0.3,
    "Blessed Orb": 0.3,
    "Orb of Transmutation": 0.02,
    "Orb of Augmentation": 0.02,
    "Mirror of Kalandra": 50000.0,
    "Awakener's Orb": 50.0,
    "Ancient Orb": 8.0,
    "Harbinger's Orb": 5.0,
    "Engineer's Orb": 0.2,
    "Stacked Deck": 1.0,
    "Simple Sextant": 1.0,
    "Prime Sextant": 2.0,
    "Awakened Sextant": 4.0,
    "Elevated Sextant": 10.0,
    "Orb of Unmaking": 1.0,
    "Veiled Chaos Orb": 3.0,
    "Fracturing Orb": 100.0,
}


async def fetch_currency_rates(league: str) -> tuple[dict[str, float], float]:
    """Fetch currency -> chaos ratios from poe.ninja.

    Returns:
        (rates_dict, divine_ratio) where rates_dict maps currency name -> chaos value,
        and divine_ratio is the chaos value of a Divine Orb.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://poe.ninja/api/data/CurrencyOverview",
                params={"league": league, "type": "Currency"},
                headers={"User-Agent": "PathOfPurpose/0.9.4"},
            )
            resp.raise_for_status()
            data = resp.json()

        rates: dict[str, float] = {"Chaos Orb": 1.0}
        lines = data.get("lines", [])
        for line in lines:
            name = line.get("currencyTypeName", "")
            # chaosEquivalent is the value of 1 unit in chaos
            chaos_val = line.get("chaosEquivalent", 0.0)
            if name and chaos_val > 0:
                rates[name] = chaos_val

        divine = rates.get("Divine Orb", FALLBACK_RATES["Divine Orb"])
        return rates, divine

    except Exception:
        # poe.ninja unavailable — use fallback rates
        return dict(FALLBACK_RATES), FALLBACK_RATES["Divine Orb"]
