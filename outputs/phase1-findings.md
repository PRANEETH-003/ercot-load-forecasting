# Phase 1 Findings — ERCOT Grid Load & Price Analysis
Working notes. Findings are stated in Teja's own framing first, then the sharpened version for the README.

## Finding 1 — Texas is a summer-evening system (DRAFT, Teja's call 2026-10-22)
Teja's reasoning: August is peak summer; on a hot day the heat peaks and everyone runs AC to
cover it, so load peaks in the evening. January is peak winter; temperatures are still low when
people reach offices and schools, so heating load lands in the morning.

Data behind it (2025, ERCOT official hourly load):
- Annual peak 83,679 MW on Aug 18 at 17:00; top 3 hours of the year are all Aug 18, 15:00–17:00
- Average daily peak: August ~80,695 MW vs January ~61,496 MW
- August weekday profile: 54,910 MW at 05:00 → 80,189 MW at 17:00
- January weekday profile: morning peak 60,932 MW at 07:00 > 54,590 MW at 17:00

Sharpenings added in session:
- Summer: air temperature peaks mid-afternoon, but load peaks ~17:00 because buildings have
  absorbed heat all day (thermal lag) and residential AC switches on as people get home while
  commercial load is still running — a coincidence of both sectors at once.
- Winter: coldest temperatures are overnight/early morning; heating systems recover buildings
  from night setback as people wake and arrive, all at the same hour. Texas heating is heavily
  electric (heat pumps + resistance backup), so cold mornings bite hard.

README version: "ERCOT is a summer-peaking system. In 2025 its load topped out at 83.7 GW on an
August evening, driven by coincident cooling demand, while winter demand peaked on cold
mornings at roughly three-quarters of the summer level."

## Finding 2 — Two metros carry the peak (Teja's call 2026-10-22)
Teja's reasoning: the two metro zones hold not just homes and schools but also large
industries, so total demand concentrates there.

Data behind it (at the Aug 18 17:00 system peak):
- North Central (Dallas–Fort Worth) 26,582 MW + Coast (Houston) 22,349 MW = ~58% of the system peak
- Top 3 zones (incl. South Central, Austin/San Antonio, 14,520 MW) = ~76%
- All three sat at 97–98% of their OWN annual peaks in the same hour

Sharpening added in session: industrial load runs 24/7, so industry sets a zone's LEVEL
(high base load — Houston's refineries/petrochemical base, DFW's population/commercial scale).
It does not set the PEAK: if industry ruled, Houston's peak would not land on a hot August
evening at 97% of its annual max in the same hour as everyone else's. Weather sets the peak.

README version: "Texas demand is concentrated: Dallas–Fort Worth and Houston alone are about
58% of the system peak. Industry and population set the level, but the peak itself is weather —
on August 18 all three big metro zones hit 97–98% of their annual maxima in the same hour."

Bonus observation (feeds Phase 2): on Aug 18 load climbed ~28 GW (+50%) from the 04:00 floor
(55,715 MW) to the 17:00 peak — the daily ramp a forecaster has to predict.

Supporting analysis from session (Teja's ocean question, 2026-10-22):
- Gulf humidity raises Houston's cooling load (latent load on AC + muggy nights). August 3 AM
  load as % of 5 PM load: Coast 69% vs North Central 61% — Houston gets less overnight relief.
- The ocean also explains industry location (port/Ship Channel) — so it feeds the LEVEL too.
- Control case: Far West (Permian oil & gas) runs at 98% of its evening level at 3 AM — pure
  industrial load has no weather shape at all. Houston's 69% = industry base + weather cycle.
- Honest limit: load-only data can't fully separate humidity-flat from industry-flat; dew point
  is the variable a forecaster would add (Phase 2 feature discussion).

## Finding 3 — TBD (price-spike conditions, needs DAMLZHBSPP_2025)
