# Scoring System Overview

The project separates production scores from shadow research scores.

Production:

- `decision_score` is the current production decision score.
- Production ranking remains unchanged in the open-source cleanup.
- `production_change_allowed` is false.

Shadow research:

- `stock_short_score_v2`
- `shadow_decision_score_v3`
- `shadow_decision_score_v4`
- `defensive_shadow_score`
- `regime_router_shadow_score_v5`

V5 status:

- Promotion gate: `review_ready`
- Production enabled: false
- Meaning: ready for human review, not automatic adoption

All scoring output is for research and validation. It is not investment advice.
