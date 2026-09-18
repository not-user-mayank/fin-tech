# Fintech — Micro-Merchant Credit Score & UPI Anomaly Detector

A two-person collaboration (Person A + Person B) to build a Streamlit-based risk dashboard that scores merchants using dummy/real UPI transaction data and detects anomalies (high velocity, large outliers, etc.).

## Project Structure

```
fintech-project/
├── app.py                 # Streamlit dashboard (Person A) — login, health analysis, peak detection, charts
├── anomaly.py             # Anomaly detection rules (Person B) — velocity, outlier, flag logic
├── scoring.py             # Credit scoring / risk band logic (Person B)
├── generate_data.py       # Synthetic UPI transaction generator (Person B)
├── data/
│   ├── transactions.csv   # Raw / dummy UPI transaction feed
│   └── final.csv          # Processed dataset (post-scoring / flagging)
├── backend/               # Cloned reference copy of Person B's repo (https://github.com/YBY7B7B6GBUGFRJO/backend)
└── requirements.txt       # Core dependencies
```

## Features (App)

- **Login** — simple auth (`admin` / `password123`) before dashboard access
- **Merchant Health Analysis** — explains why a merchant is high/low risk
- **Risk Score & Loan Limits** — score cards per merchant (Person B's scoring integration)
- **Anomaly Peak Detection** — bar chart of top 3 days with the most anomalies
- **Flagged Transactions Table** — anomaly reasons (`high_velocity`, `threshold_amount`, `large_outlier`)
- **Interactive Charts** — amount over time, amount vs score (scatter), risk band distribution (pie)

## Dependencies

```bash
python -m pip install -r requirements.txt
```

Core packages: `streamlit`, `pandas`, `numpy`, `plotly`, `matplotlib`

## Run

```bash
streamlit run app.py
```

Access at `http://localhost:8501`

## Team

- **Person A (Dashboard / Deployment)** — `https://github.com/not-user-mayank/fin-tech`
- **Person B (Backend / Data)** — `https://github.com/YBY7B7B6GBUGFRJO/backend`

## Status

- ✅ Step 1 — Dependencies installed and verified
- ✅ Step 2 — Dashboard skeleton with dummy data
- ✅ Step 3 — Login + merchant health analysis + anomaly peak detection
- ✅ Merge — Person B backend (`anomaly.py`, `scoring.py`, `generate_data.py`, `data/`) integrated
- ⏸ Project running; ready for Person B live module updates
