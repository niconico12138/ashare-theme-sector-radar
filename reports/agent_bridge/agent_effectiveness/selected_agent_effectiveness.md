# Agent Effectiveness Evaluation Report

**Evaluation Date**: 2026-07-06T16:22:14.014246
**Dates Evaluated**: 2026-07-01, 2026-07-02, 2026-07-03, 2026-07-06
**Preset**: selected

## Per-Agent Effectiveness

| Agent | Total | Success | Fallback | Failed | Success Rate | Buy | Hold | Sell | Avg Confidence | Rating |
|-------|-------|---------|----------|--------|--------------|-----|------|------|----------------|--------|
| technical_analyst | 45 | 35 | 10 | 0 | 77.8% | 0 | 0 | 1 | 55.0 | moderate |
| fundamentals_analyst | 45 | 45 | 0 | 0 | 100.0% | 0 | 0 | 8 | 51.9 | high_value |
| valuation_analyst | 45 | 44 | 1 | 0 | 97.8% | 9 | 0 | 0 | 86.7 | high_value |
| sentiment_analyst | 45 | 12 | 33 | 0 | 26.7% | 1 | 0 | 3 | 98.6 | weak |
| china_youzi | 45 | 45 | 0 | 0 | 100.0% | 32 | 0 | 5 | 31.0 | high_value |
| industry_rotation | 45 | 16 | 29 | 0 | 35.6% | 14 | 0 | 1 | 55.0 | weak |
| news_sentiment_analyst | 45 | 45 | 0 | 0 | 100.0% | 45 | 0 | 0 | 23.9 | high_value |

## Daily Top10

## Cross-Date Analysis

- **Dates evaluated**: 4
- **Total unique stocks in Top10**: 30
- **New entries**: 24

### Repeated in Top10

| Code | Appearances |
|------|-------------|
| 000062 | 3 |
| 000536 | 2 |
| 000565 | 2 |
| 000553 | 2 |
| 600196 | 2 |
| 000153 | 2 |

## Conclusions

- **High value agents**: fundamentals_analyst, valuation_analyst, china_youzi, news_sentiment_analyst
- **Weak agents**: sentiment_analyst, industry_rotation
- **Mostly fallback agents**: None
- **No data agents**: None

### Recommended Selected Preset

Keep all 7 agents: technical_analyst, fundamentals_analyst, valuation_analyst, sentiment_analyst, china_youzi, industry_rotation, news_sentiment_analyst
