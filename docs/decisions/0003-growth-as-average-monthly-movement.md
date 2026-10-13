# 0003 — Growth Q1 → Q2 uses average monthly movement, not totals

**Status:** accepted

**Context.** Some cities are missing months. Tabuk has no April, and Sudair has no April or May. Comparing quarter **totals** would show these cities "shrinking" just because they have fewer months of data.

**Decision.** Growth = average monthly movement in Q2 ÷ average monthly movement in Q1 − 1. It is calculated only for cities with data in both quarters. Missing months are shown as gaps (`traffic_coverage.csv`, Data quality tab) and are never filled.

**Consequences.**
- Fair comparison across cities. Today: Madn Oasis Jeddah +25%, Riyadh 2nd +19%, Tabuk −5%.
- A city with only one month in a quarter gets a less stable average. The city profile shows month coverage so the reader can judge.
- Entry/exit imbalance above 30% is flagged as a quality warning. The numbers are not changed.
