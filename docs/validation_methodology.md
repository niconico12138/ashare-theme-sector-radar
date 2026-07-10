# Validation Methodology

Selection validation compares candidate scores against next-day forward returns when forward data is available.

Key metrics:

- Top-bottom return gap.
- Hit-rate difference.
- Spearman rank correlation.
- Date-level consistency.
- Market-regime split: `broad_up`, `broad_down`, `mixed`.
- Outlier contribution checks.
- Bucket monotonicity.

Interpretation rules:

- A positive historical gap is evidence for research, not a trading signal.
- 120 valid days is useful but still not enough for automatic production changes.
- Shadow scores must remain shadow-only until separately reviewed and approved.
- `review_ready` does not equal `production_enabled`.

Current boundary:

- production decision score unchanged.
- production ranking unchanged.
- production_change_allowed = false.
