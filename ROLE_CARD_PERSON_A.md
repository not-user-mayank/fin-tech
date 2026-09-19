# ROLE CARD — PERSON A (Dashboard / Deployment / Integration / APIs)

## What you own
- **app.py** — Streamlit dashboard (`streamlit run app.py`): login, merchant selector, risk cards, trend charts, anomaly table, health analysis, peak detection, explainability charts
- **README.md** — project docs, instructions, links to both repos
- **Integration** — importing `scoring.compute_credit_score` and `anomaly.flag_transactions` into dashboard
- **Deployment** — Streamlit deployment / future APIs for lender integration

## Your contract (hard interface to Person B)
- Call `scoring.compute_credit_score(df)` when available; graceful fallback (`try/except`) if file missing
- Call `anomaly.detect_anomalies(df)` (or use `anomaly.flag_transactions`) when available
- Use `credit_score` (300–900), `weighted_sum`, `feature_contributions` for explainability charts
- Use `is_flagged` / `flag_reason` for flagged-transaction table
- Your `app.py` must stay independent of Person B's internal code; you only depend on public outputs (`credit_score`, `weighted_sum`, etc.)

## Your workflow
1. Your `app.py` already has the dashboard (login, health analysis, peak detection, charts)
2. When Person B updates `scoring.py` or `anomaly.py`: pull, run, verify
3. Commit / push your dashboard changes to `https://github.com/not-user-mayank/fin-tech`

## Your next tasks
- Add `feature_contributions` visualization in dashboard (bar chart + text explanation for "why this score")
- Confirm `compute_credit_score` output integrates cleanly with current chart logic (`scatter`, `line`, `pie` using `score` / `credit_score` column names)
- Prepare API key / future integration notes (Open AI / fraud-check API for future use)
