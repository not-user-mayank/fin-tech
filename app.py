import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta
import streamlit as st

# ---------- Ready for Person B modules ----------
try:
    from anomaly import detect_anomalies
except ImportError:
    detect_anomalies = None

try:
    from scoring import compute_credit_score
except ImportError:
    compute_credit_score = None

st.set_page_config(page_title="Fintech Risk Dashboard", layout="wide")
st.title("Fintech Risk Dashboard")

# ---------- Dummy data generation (no external files yet) ----------
def generate_dummy_transactions(n_rows=2000, n_merchants=20, seed=42):
    np.random.seed(seed)
    merchant_ids = [f"M{i:03d}" for i in range(1, n_merchants + 1)]
    payer_ids = [f"P{i:04d}" for i in range(1, 201)]

    amounts = np.round(np.random.exponential(scale=500, size=n_rows), 2)
    amounts = np.clip(amounts, 10, 10000)

    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    timestamps = [
        start_date + timedelta(seconds=int(np.random.uniform(0, (end_date - start_date).total_seconds())))
        for _ in range(n_rows)
    ]
    timestamps.sort()

    df = pd.DataFrame({
        "txn_id": [f"T{i:06d}" for i in range(1, n_rows + 1)],
        "merchant_id": np.random.choice(merchant_ids, size=n_rows),
        "payer_id": np.random.choice(payer_ids, size=n_rows),
        "amount": amounts,
        "timestamp": timestamps,
        "status": np.random.choice(
            ["completed", "completed", "completed", "failed", "pending"],
            size=n_rows
        ),
        # Dummy anomaly/score columns for UI testing
        "has_anomaly": np.random.choice([True, False], size=n_rows, p=[0.05, 0.95]),
        "anomaly_score": np.round(np.random.uniform(0, 1, size=n_rows), 4),
        "credit_score": np.round(np.random.uniform(300, 850, size=n_rows), 2),
        "is_flagged": np.random.choice([True, False], size=n_rows, p=[0.05, 0.95]),
        "flag_reason": np.where(
            np.random.choice([True, False], size=n_rows, p=[0.05, 0.95]),
            np.random.choice(["high_velocity", "threshold_amount", "large_outlier"], size=n_rows),
            ""
        ),
        "score": np.round(np.random.uniform(0, 100, size=n_rows), 2),
        "risk_band": np.random.choice(["low", "medium", "high"], size=n_rows, p=[0.6, 0.3, 0.1]),
        "loan_limit": np.round(np.random.uniform(50000, 500000, size=n_rows), 2),
    })
    return df

# Load dummy data
@st.cache_data
def load_data():
    return generate_dummy_transactions()

df = load_data()

# ---------- Sidebar: merchant selection ----------
st.sidebar.header("Filters")
merchants = sorted(df["merchant_id"].unique())
selected_merchant = st.sidebar.selectbox("Select Merchant", merchants)

# Filter to selected merchant
dff = df[df["merchant_id"] == selected_merchant].copy()

if dff.empty:
    st.warning("No transactions for this merchant.")
    st.stop()

# ---------- Aggregate score per merchant (dummy logic for now) ----------
avg_score = dff["score"].mean()
risk_band_mode = dff["risk_band"].mode()[0] if not dff["risk_band"].empty else "unknown"
avg_loan_limit = dff["loan_limit"].mean()

# --- Real module integration stubs ---
if compute_credit_score is not None:
    dff = compute_credit_score(dff)
if detect_anomalies is not None:
    dff = detect_anomalies(dff)

# Anomaly summary
anomaly_count = dff["has_anomaly"].sum() if "has_anomaly" in dff.columns else dff["is_flagged"].sum()

# ---------- Main layout ----------
st.header(f"Merchant: {selected_merchant}")

# Score card
st.subheader("Risk Score & Limits")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Average Risk Score", f"{avg_score:.1f}")
with col2:
    st.metric("Risk Band", risk_band_mode)
with col3:
    st.metric("Avg Loan Limit", f"₹{avg_loan_limit:,.0f}")

# Risk gauge (progress bar)
st.progress(int(avg_score))

# Anomaly quick stats
if anomaly_count > 0:
    st.warning(f"⚠ {int(anomaly_count)} anomalous transactions detected for this merchant.")
else:
    st.success("✅ No anomalies detected.")

# Trend chart (Plotly interactive)
st.subheader("Transaction Amount Over Time")
chart_df = dff.set_index("timestamp")[["amount"]].sort_index()
fig_amount = px.line(chart_df, x=chart_df.index, y="amount", title="Amount vs Time")
st.plotly_chart(fig_amount, use_container_width=True)

# Scatter: amount vs score
st.subheader("Amount vs Risk Score")
fig_scatter = px.scatter(dff, x="score", y="amount", color="risk_band",
                         title="Amount vs Risk Score by Band",
                         hover_data=["txn_id", "payer_id"])
st.plotly_chart(fig_scatter, use_container_width=True)

# Risk band distribution
st.subheader("Risk Band Distribution")
fig_band = px.pie(dff, names="risk_band", title="Risk Band Breakdown",
                  hole=0.4)
st.plotly_chart(fig_band, use_container_width=True)

# Flagged transactions table
st.subheader("Flagged Transactions")
flagged = dff[dff["is_flagged"] == True]
if flagged.empty:
    st.info("No flagged transactions for this merchant.")
else:
    st.dataframe(
        flagged[["txn_id", "payer_id", "amount", "timestamp", "status", "flag_reason", "anomaly_score"]]
    )

# All transactions (optional, collapsible)
with st.expander("View all transactions for this merchant"):
    st.dataframe(
        dff[["txn_id", "payer_id", "amount", "timestamp", "status"]]
    )