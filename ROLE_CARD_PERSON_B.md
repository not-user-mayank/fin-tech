# ROLE CARD — PERSON B (Backend / Data / Modeling)

## What you own
- **generate_data.py** — synthetic UPI transaction feed (`data/transactions.csv`)
- **anomaly.py** — `flag_transactions(df) -> df` (adds `is_flagged` bool, `flag_reason` str)
- **scoring.py** — `compute_credit_score(df) -> df` (adds `credit_score`, `weighted_sum`, `risk_band`, `loan_limit`, `feature_contributions`, sub-scores `0–1`)

## Your contract (hard interface)
### `scoring.py`
- Input: dataframe with at least `txn_id`, `merchant_id`, `payer_id`, `amount`, `timestamp`, `status`, `is_flagged`
- Must return: all input columns + `credit_score` (int 300–900), `weighted_sum` (float 0–1), `feature_contributions` (dict/string for explainability), `risk_band` (`low`/`moderate`/`high`/`decline`), `loan_limit` (int), `clean_txns` info for cold-start cap
- Must compute **only from clean transactions** (`~df["is_flagged"]`)
- Must implement the 7-feature weighted scorecard exactly (weights in source code: `W` dict — see scoring.py `W` dict in the project)
- Must handle cold-start cap (< 30 clean transactions → cap score at 650, not 750+ or 550-649)
- Must include explainability contributions for the "why this score" chart in `app.py`

### `anomaly.py`
- `flag_transactions(df: pd.DataFrame) -> pd.DataFrame`
- Must flag: `threshold_amount` (amount ∈ {999,1499,1999,2499}), `high_velocity` (payer count >= 10), `large_outlier` (amount > 3× merchant median)

### `generate_data.py`
- Must write `data/transactions.csv` deterministically (seed 42) with schema: `txn_id`, `merchant_id`, `payer_id`, `amount`, `timestamp`, `status`
- Must include velocity bursts (near-threshold amounts) and realistic failure/pending ratios

## Your workflow
1. Read `scoring.py` (already complete with weighted formula) — verify it runs against your data
2. Read `anomaly.py` (already complete) — verify rules match spec
3. If you change anything: commit + push to `https://github.com/YBY7B7B6GBUGFRJO/backend`
4. You do NOT edit `app.py` (Person A owns the dashboard / deployment / UI)

## Your next task
- Ensure your `scoring.py` computes score exactly: `Score = 300 + 600 * weighted_sum`
- Ensure sub-scores `0–1` (min-max normalized within merchant population, or absolute scale if absolute values make sense)
- Ensure explainability string shows points per feature (`+150 from active_days`, `-80 from diversity`, etc.)
- Confirm `feature_contributions` column is a readable dict or JSON that the dashboard can render as a bar/text explanation in the "why this score" section
