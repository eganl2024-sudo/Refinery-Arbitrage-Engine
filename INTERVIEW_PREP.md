# Refinery Arbitrage Engine — Interview Prep

## 30 Seconds

I built a live refinery economics dashboard that computes the 3:2:1 crack spread from real-time futures prices, strips out NatGas variable costs and fixed OpEx to get net refining margin, and runs an EV/EBITDA model to translate margin changes into implied stock price impacts for Valero and Phillips 66. The analytical decision I made that I'm most confident in: I use daily returns correlation between the spread and equity, not price levels correlation — because both series trend upward over time, and levels correlation confounds the fundamental link with shared drift. Returns isolates what actually moves together day-to-day.

---

## 60 Seconds

I built a live refinery margin analytics platform that ingests WTI, RBOB gasoline, and heating oil futures prices from yfinance and computes the 3:2:1 crack spread — two barrels of gasoline plus one barrel of distillate from three barrels of crude, which approximates the US Gulf Coast refinery output mix. I then strip out variable OpEx — natural gas energy intensity at 0.45 MMBtu per barrel — and fixed OpEx at six dollars per barrel to get net refining margin.

The equity impact model translates a spread scenario into EBITDA impact using throughput times capture rate times 365 days, then divides by shares at a given EV/EBITDA multiple. The insight that shaped the correlation section: I show returns correlation as the headline metric rather than price levels, because both crack spreads and refiner equities trend upward over multi-year periods — crude cycles on one hand, buybacks and earnings growth on the other. That shared upward drift inflates the Pearson coefficient when measured on price levels. Daily percentage returns removes that bias and shows the actual day-to-day fundamental link.

I also tested Granger causality between weekly EIA sentiment and crack spreads — and the non-significant result is the actual finding. It's consistent with semi-strong market efficiency: EIA data is public and gets priced into front-month futures within minutes.

---

## 120 Seconds

I built a refinery arbitrage analytics engine that combines live futures data, an operational cost model, equity correlation analysis, and a valuation sensitivity framework into a single dashboard. Let me go through the key decisions.

The spread formula is the 3:2:1 crack spread: two barrels of RBOB gasoline plus one barrel of heating oil minus three barrels of WTI crude, divided by three. That ratio reflects the US Gulf Coast refinery yield structure — more gasoline-heavy than distillate-heavy. I also built in 5:3:2 and 2:1:1 formula toggles for different refinery configurations, computed on the fly from the stored RBOB and heating oil price columns.

Net refining margin is the crack spread minus variable OpEx — natural gas at 0.45 MMBtu per barrel, which is the industry-standard refinery energy intensity for a hydroskimming configuration — minus six dollars per barrel for fixed costs. That six dollar figure is realistic for a complex Gulf Coast refinery running at high utilization.

For the equity model, I use ΔEBITDA equals delta spread times throughput times capture rate times 365, then ΔEV equals ΔEBITDA times the EV/EBITDA multiple, and implied ΔP equals ΔEV divided by shares. I built this separately for Valero and Phillips 66 because they have materially different throughput and capture rate profiles — VLO is a pure-play refiner so the spread-to-equity translation is tighter.

The correlation section was where I made the most deliberate analytical choice. I present returns correlation as the headline number, not price levels. Both crack spreads and refiner stocks trend upward over multi-year periods — crack spreads follow commodity cycles, equities compound through buybacks and earnings growth. That shared drift inflates the Pearson coefficient on levels — you can get a correlation of 0.7 that's mostly reflecting secular trends rather than fundamental linkage. Daily returns correlation removes that and gives you a number you can actually trade on.

Two things were unexpected. First, I ran Granger causality between weekly EIA sentiment scores and the crack spread at lags of one to four weeks, and the test consistently comes back non-significant. I expected some predictive signal. But the non-significance is actually the correct result under semi-strong market efficiency — EIA data is public and gets priced into front-month futures within minutes of release. Publishing a significant result there would have been wrong. Second, capture rate turned out to be the most sensitive valuation parameter — more sensitive than throughput or the spread level itself, because it compounds multiplicatively with both.
