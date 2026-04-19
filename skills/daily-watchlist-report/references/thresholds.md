# Thresholds reference

Thresholds decide what gets flagged vs. stays quiet. The defaults are tuned to produce a report with roughly 10-20% of tickers flagged on a normal day and more during busy sessions.

## Defaults

| Threshold           | Default | What it catches                                     |
|---------------------|---------|-----------------------------------------------------|
| `price_move_pct`    | 3.0     | Any single-session |move| ≥ this                    |
| `window_move_pct`   | 7.0     | Cumulative move over catch-up window (for skips)    |
| `volume_multiple`   | 2.0     | Volume ≥ Nx the 20-day average                      |
| `rsi_overbought`    | 70      | RSI(14) at/above — potential mean-reversion setup   |
| `rsi_oversold`      | 30      | RSI(14) at/below                                    |
| `sentiment_delta`   | 0.3     | Daily news sentiment shift (EODHD sentiment, -1..1) |

52-week highs/lows are always flagged when the ticker's position in the 52w range is ≥ 0.98 or ≤ 0.02.

## Tuning by cluster type

### Low-vol / defensive (COST, BRK-B, NEE)
```yaml
thresholds:
  price_move_pct: 2.0
  volume_multiple: 1.8
```
A 3% move in COST is already very notable, and volume spikes are meaningful at lower multiples.

### Standard large-cap (NVDA, AVGO, TSM)
Use defaults.

### Small-cap / speculative (RKLB, ASTS, small biotech)
```yaml
thresholds:
  price_move_pct: 5.0
  volume_multiple: 2.5
  window_move_pct: 12.0
```
These names routinely move 4-5% on noise. Raise the floor or the report will be all noise.

### Crypto-adjacent (COIN, MSTR, MARA)
```yaml
thresholds:
  price_move_pct: 5.0
  window_move_pct: 15.0
```
Moves track BTC more than company fundamentals.

## Calibration tip

After a week of running the skill, count: are there too many flags to read, or too few to bother? Adjust `price_move_pct` up or down by 0.5 and iterate. The goal is a report you *actually read every morning* — not a perfect signal detector.

## What's always flagged regardless of thresholds

- **Any 8-K filing** in the window (material event by SEC definition)
- **Upcoming earnings within 7 days** (catalyst, not a flag on current data)
- **EODHD-scored news with |sentiment| > 0.6** (very strong positive or negative)

These can't be tuned off — they're categorically high-signal.
