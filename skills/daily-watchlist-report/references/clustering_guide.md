# Clustering guide

When the user has a flat list and wants to group it into investment themes, use this guide.

## The principle: cluster by *driver*, not by GICS sector

GICS sectors (Tech, Financials, Energy) are too coarse — NVDA and CSCO are both "Tech" but move on completely different drivers. Instead, cluster by **what macro/secular force moves the stock**.

Good cluster examples:
- **AI infrastructure** (hyperscaler capex): NVDA, AVGO, VRT, DELL, SMCI, ANET, MU
- **DRAM/HBM** (memory pricing cycle): MU, 000660.KS (SK Hynix), 005930.KS (Samsung)
- **Space** (launch cadence + defense budgets): RKLB, ASTS, LMT, BA
- **Clean energy — residential solar** (rate-sensitive + policy): ENPH, RUN, NOVA
- **Clean energy — utility scale**: FSLR, NEE, AES
- **GLP-1 / obesity**: LLY, NVO
- **Cybersecurity** (enterprise IT budgets): CRWD, PANW, S, ZS
- **Data center REITs**: EQIX, DLR
- **Commodities — copper** (electrification demand): FCX, SCCO
- **Defensive compounders**: COST, BRK-B, WMT

Bad cluster examples (too broad, driver isn't shared):
- "Tech" — meaningless, drivers are totally different across subsectors
- "Growth" — a style, not a driver
- "My long-term holds" — organizational, not a thesis

## Process for clustering a flat list

1. For each ticker, ask: **"Why do I own/watch this? What force would make me buy more?"** That's the cluster.
2. If two tickers have the same answer → same cluster.
3. If a ticker has *multiple* valid answers (MU is both DRAM and AI infra), put it in both. The report will show it under each.
4. Write a one-sentence thesis per cluster. This is critical — it's what the report frames news *against*. A cluster without a thesis is just a folder.
5. Leave genuinely uncategorized names (e.g. a defensive anchor you just hold) in `uncategorized`. Don't force-fit.

## Thresholds per cluster

Different clusters have different natural volatility:
- **Megacap compounders** (COST, BRK-B): use 2% price threshold — 3% is already a notable move
- **Standard large-caps**: 3% default
- **Small-cap / speculative** (space, gene therapy, early-stage fusion): 5-7% — noise floor is higher

Set `thresholds:` inside the cluster in `watchlist.yaml` to override the global default.

## When to re-cluster

- When your thesis on a name changes (you now own NVDA for AI infra, not gaming)
- When a new theme emerges in your thinking that spans existing tickers
- Roughly every 3-6 months as a hygiene check

The clustering is not precious — it's a tool for organizing attention. Rearrange freely.
