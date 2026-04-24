# Scoring Model

## Structure

Raw positive score (max 90) across 5 buckets, then gated by risk multiplier:

```
final_score = raw_positive × risk_multiplier − overheat_penalty + continuity_adj
```

| Bucket             | Max  | Key signals                                              |
|--------------------|------|----------------------------------------------------------|
| Technical          | 30   | T-bottom, double bottom, poking, volume, MA stack        |
| Flow stage         | 20   | Stage appropriateness + continuity from prior stage      |
| Multi-timeframe    | 15   | Monthly base + weekly trend + daily timing               |
| Fundamental dir.   | 15   | Revenue/OP growth direction, op leverage, margin, debt   |
| Theme/sector       | 10   | Sector strength, theme momentum, peer confirmation       |
| **Risk (gate)**    | 0–10 | Not added — used as multiplier 1.0 → 0.55               |

## Technical Bucket (30 pts)

| Sub-score          | Max  |
|--------------------|------|
| Base reversal      | 8    |
| Candle quality     | 5    |
| MA structure       | 5    |
| Breakout confirm   | 6    |
| Volume quality     | 4    |
| Overheat penalty   | -2   |

## Flow Bucket (20 pts)

| Sub-score              | Max  |
|------------------------|------|
| Stage appropriateness  | 8    |
| Continuity             | 6    |
| Late-stage penalty     | -6   |

Stage entry weights: T바닥=0.95, 포킹=1.00, 재랠리=0.85, 역배열재매집=0.75,
펌핑=0.80, 랠리=0.55, 관찰=0.30, **과열=0.10**.

## Risk Gate

Risk score 0–10 → multiplier curve:

| Risk score | Multiplier |
|------------|------------|
| 0          | 1.00       |
| 5          | 0.78       |
| 10         | 0.55       |

## Overrides (applied after scoring)

| Condition                          | Override                           |
|------------------------------------|------------------------------------|
| Stage = 과열                       | Never Strong Buy; -15 penalty      |
| stop_loss.price = None             | Downgrade to Watch for Confirmation|
| confidence_score < 0.4             | Downgrade one level                |
| Flow continuity ≤ 2.5              | -5 pts continuity adjustment       |
| Flow continuity ≥ 5.5              | +2 pts continuity adjustment       |

## Action Mapping

| Score     | Action                         |
|-----------|--------------------------------|
| 85–100    | Strong Buy Setup               |
| 70–84     | Buy on Pullback                |
| 55–69     | Watch for Confirmation         |
| 40–54     | Hold / No Immediate Entry      |
| 0–39      | Avoid / Overheated / Weak Setup|
