import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta
import streamlit as st

# ---------- Authentication ----------
def login():
    """Simple login page with hardcoded credentials"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.username = ""
        st.session_state.password = ""
    
    if not st.session_state.authenticated:
        st.header("Login to Fintech Risk Dashboard")
        st.write("Please log in to access the dashboard")
        
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            # Simple hardcoded credentials for demo
            if username == "admin" and password == "password123":
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.password = password
                st.success("Login successful!")
            else:
                st.error("Invalid credentials")
        return False
    return True

# Auth handled by tabs below; keep old guard non-blocking
_ = login()  # legacy guard

# ---------- Ready for Person B modules ----------
try:
    from anomaly import flag_transactions as detect_anomalies
except ImportError:
    detect_anomalies = None

try:
    from scoring import compute_credit_score
except ImportError:
    compute_credit_score = None

st.set_page_config(page_title="Fintech Risk Dashboard", layout="wide")
st.title("Fintech Risk Dashboard")

# ---------- Signup / Bank Details ----------
if "user_profile" not in st.session_state:
    st.session_state.user_profile = {}

# Show signup/login tabs at top before anything else
if not st.session_state.get("authenticated", False):
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    with tab1:
        st.subheader("Login")
        if st.button("Continue as Guest", type="primary"):
            st.session_state.authenticated = True
            st.session_state.username = "guest"
            st.session_state.user_profile["name"] = "Guest User"
            st.session_state.signup_done = True
            st.rerun()
    with tab2:
        st.subheader("Sign Up (Dummy — any details accepted)")
        name = st.text_input("Name", value=st.session_state.user_profile.get("name", ""))
        email = st.text_input("Email", value=st.session_state.user_profile.get("email", ""))
        mobile = st.text_input("Mobile", value=st.session_state.user_profile.get("mobile", ""))
        if st.button("Complete Signup", type="primary"):
            st.session_state.authenticated = True
            st.session_state.username = email or name
            st.session_state.user_profile.update({
                "name": name,
                "email": email,
                "mobile": mobile,
            })
            st.session_state.signup_done = True
            st.rerun()
    st.stop()

# After signup/login, collect bank + PAN details (dummy, optional)
if st.session_state.get("signup_done", False):
    with st.sidebar:
        st.subheader("Bank & PAN Details (Dummy)")
        bank = st.text_input("Bank Name", value=st.session_state.user_profile.get("bank", ""))
        acct = st.text_input("Account No", value=st.session_state.user_profile.get("acct", ""))
        ifsc = st.text_input("IFSC", value=st.session_state.user_profile.get("ifsc", ""))
        pan = st.text_input("PAN", value=st.session_state.user_profile.get("pan", ""))
        st.session_state.user_profile.update({"bank": bank, "acct": acct, "ifsc": ifsc, "pan": pan})
        if bank and acct:
            st.info("Profile saved.")


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

# Theme mode toggle (light/dark)
if "light_mode" not in st.session_state:
    st.session_state.light_mode = False

# Theme toggle in sidebar (before filters if needed)
with st.sidebar:
    st.toggle("Light Mode", value=st.session_state.light_mode, key="light_toggle")
    if "light_toggle" in st.session_state:
        st.session_state.light_mode = st.session_state.light_toggle

# Dynamic color variables
if st.session_state.light_mode:
    bg_color = "#f8f9fa"
    text_color = "#212529"
    sidebar_bg = "#ffffff"
    card_bg = "#ffffff"
    header_bg = "#e3f2fd"
else:
    bg_color = "#111111"
    text_color = "#ffffff"
    sidebar_bg = "#1a1a2e"
    card_bg = "#0e0e24"
    header_bg = "#1e1e2f"

# Inject theme CSS + premium styling
st.markdown(
    f"""<style>
    /* base */
    [data-testid="stAppViewContainer"] {{
        background-color: {bg_color} !important;
        color: {text_color} !important;
        font-family: 'Segoe UI', system-ui, sans-serif;
    }}
    [data-testid="stSidebar"] {{
        background-color: {sidebar_bg} !important;
        color: {text_color} !important;
    }}
    .stCard, .stExpander, .stInfo, .stSuccess, .stWarning, .stError {{
        background-color: {card_bg} !important;
        color: {text_color} !important;
        border-radius: 12px !important;
        border: 1px solid {'#dee2e6' if st.session_state.light_mode else '#333'} !important;
    }}
    .stHeader header, .stTitle, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{
        color: {text_color} !important;
    }}

    /* hero title */
    .hero-title {{
        font-size: 2.4rem;
        font-weight: 800;
        color: {text_color};
        margin-bottom: 0;
        letter-spacing: -0.02em;
    }}
    .hero-sub {{
        color: {text_color};
        font-size: 1rem;
        opacity: 0.75;
        margin-top: -8px;
        margin-bottom: 24px;
    }}

    /* score cards */
    .score-card {{
        border-radius: 16px !important;
        padding: 20px 16px !important;
        text-align: center;
        color: #fff !important;
        box-shadow: 0 4px 24px rgba(0,0,0,0.18) !important;
        transition: transform 0.2s;
    }}
    .score-card:hover {{
        transform: translateY(-4px) !important;
    }}
    .score-label {{
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        opacity: 0.9;
    }}
    .score-value {{
        font-size: 2.4rem;
        font-weight: 800;
        line-height: 1.15;
    }}
    .score-band {{
        display: inline-block;
        margin-top: 6px;
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.5px;
    }}
    .band-low      {{ background: linear-gradient(135deg,#00c853,#00e676); color:#000; }}
    .band-moderate {{ background: linear-gradient(135deg,#ffd600,#ffea00); color:#000; }}
    .band-high     {{ background: linear-gradient(135deg,#ff6d00,#ff9100); color:#000; }}
    .band-decline  {{ background: linear-gradient(135deg,#d50000,#ff1744); color:#fff; }}

    /* KPI row */
    .kpi {{
        flex: 1 1 140px;
        background: {card_bg};
        border: 1px solid {'#dee2e6' if st.session_state.light_mode else '#333'};
        border-radius: 14px;
        padding: 14px 18px;
        text-align: center;
        box-shadow: 0 2px 12px rgba(0,0,0,0.10);
    }}
    .kpi-label {{ font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: 0.8px; }}
    .kpi-value {{ font-size: 1.6rem; font-weight: 700; color: {text_color}; }}

    /* upload box */
    .upload-box {{
        border: 2px dashed {'#ced4da' if st.session_state.light_mode else '#555'};
        border-radius: 16px;
        padding: 28px;
        text-align: center;
        background: {sidebar_bg};
        margin-bottom: 20px;
    }}

    /* explanation */
    .expl-box {{
        background: {sidebar_bg};
        border-left: 4px solid #667eea;
        border-radius: 8px;
        padding: 14px 18px;
        margin-top: 12px;
        color: {text_color};
    }}

    /* chart wrap */
    .chart-wrap {{
        background: {card_bg};
        border-radius: 14px;
        padding: 16px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.10);
        margin-bottom: 20px;
    }}

    /* section heading */
    .section-heading {{
        font-size: 1.35rem;
        font-weight: 700;
        margin-bottom: 12px;
        color: {text_color};
        border-bottom: 2px solid {'#dee2e6' if st.session_state.light_mode else '#444'};
        padding-bottom: 6px;
    }}

    /* animation */
    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(12px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
    }}
    .fade-in {{
        animation: fadeIn 0.5s ease-out both;
    }}

    /* buttons */
    .stButton>button, .stButton>button:hover {{
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: #fff !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 600 !important;
        padding: 0.4rem 1.2rem !important;
        box-shadow: 0 2px 8px rgba(102,126,234,0.35) !important;
        transition: all 0.15s ease !important;
    }}
    .stButton>button:hover {{
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 12px rgba(102,126,234,0.45) !important;
    }}

    /* scrollbar */
    ::-webkit-scrollbar {{ width: 8px; }}
    ::-webkit-scrollbar-track {{ background: {bg_color}; }}
    ::-webkit-scrollbar-thumb {{ background: #667eea; border-radius: 4px; }}
    </style>""",
    unsafe_allow_html=True,
)

# store mode for use below
light_mode = st.session_state.light_mode

# Load real data + Person B pipeline
@st.cache_data(show_spinner=False)
def load_data():
    df_real = pd.read_csv("data/transactions.csv", parse_dates=["timestamp"])
    if detect_anomalies is not None:
        df_real = detect_anomalies(df_real)
    if compute_credit_score is not None:
        df_real = compute_credit_score(df_real)
    return df_real

df = load_data()

# ---------- Score a new merchant from raw data (CSV upload) ----------
st.subheader("Score a New Merchant (Raw Data)")
uploaded = st.file_uploader("Upload merchant transaction CSV", type="csv")
if uploaded is not None:
    try:
        raw_df = pd.read_csv(uploaded, parse_dates=["timestamp"])
        if compute_credit_score is not None:
            raw_scored = compute_credit_score(raw_df)
            st.success(f"Scored {raw_scored['merchant_id'].nunique()} merchant(s) from {len(raw_scored)} transactions")
            raw_summary = raw_scored[["merchant_id", "credit_score", "risk_band", "loan_limit", "weighted_sum"]].drop_duplicates()
            st.dataframe(raw_summary, use_container_width=True)
            m = raw_scored.iloc[0]
            contrib = m.get("feature_contributions", {})
            if isinstance(contrib, dict) and "explanation" in contrib:
                st.info("Why this score: " + contrib["explanation"])
        else:
            st.warning("scoring.py not available.")
    except Exception as e:
        st.error(f"Could not score this file. Expected columns: txn_id, merchant_id, payer_id, amount, timestamp, status. Error: {e}")

# ---------- Sidebar: merchant selection ----------
st.sidebar.header("Filters")
merchants = sorted(df["merchant_id"].unique())
selected_merchant = st.sidebar.selectbox("Select Merchant", merchants)

# Filter to selected merchant
dff = df[df["merchant_id"] == selected_merchant].copy()

# Real score cards from Person B pipeline
if not dff.empty:
    m = dff.iloc[0]
    credit_score = int(m.get("credit_score", 0)) if pd.notna(m.get("credit_score")) else 0
    risk_band = str(m.get("risk_band", "unknown"))
    loan_limit = int(m.get("loan_limit", 0)) if pd.notna(m.get("loan_limit")) else 0
    weighted_sum = float(m.get("weighted_sum", 0)) if pd.notna(m.get("weighted_sum")) else 0
    contrib = m.get("feature_contributions", {})
    explanation = contrib.get("explanation", "Score computed from 7 sub-scores.") if isinstance(contrib, dict) else "Score computed from 7 sub-scores."

if dff.empty:
    st.warning("No transactions for this merchant.")
    st.stop()

# ---------- Aggregate score per merchant (dummy logic for now) ----------
risk_band_mode = dff["risk_band"].mode()[0] if not dff["risk_band"].empty else "unknown"
avg_loan_limit = dff["loan_limit"].mean()


# Anomaly summary
anomaly_count = int(dff["has_anomaly"].sum()) if "has_anomaly" in dff.columns else int(dff["is_flagged"].sum()) if "is_flagged" in dff.columns else 0

# ---------- Merchant Health Analysis ----------
def analyze_merchant_health(merchant_df):
    """Analyze why a merchant is good or bad based on transaction patterns"""
    analysis = {}
    
    # Calculate metrics
    total_txns = len(merchant_df)
    flagged_txns = merchant_df[merchant_df["is_flagged"] == True] if "is_flagged" in merchant_df.columns else merchant_df.iloc[0:0]
    anomaly_txns = merchant_df[merchant_df["has_anomaly"] == True] if "has_anomaly" in merchant_df.columns else merchant_df.iloc[0:0]
    
    # Amount statistics
    avg_amount = merchant_df["amount"].mean()
    max_amount = merchant_df["amount"].max()
    min_amount = merchant_df["amount"].min()
    
    # Status breakdown
    status_counts = merchant_df["status"].value_counts()
    completed_rate = status_counts.get("completed", 0) / total_txns if total_txns > 0 else 0
    
    # Time analysis (if timestamps available)
    if "timestamp" in merchant_df.columns:
        merchant_df_sorted = merchant_df.sort_values("timestamp")
        # Detect peaks: days with highest anomaly count
        merchant_df_sorted["date"] = merchant_df_sorted["timestamp"].dt.date
        daily_anomalies = merchant_df_sorted.groupby("date")["has_anomaly"].sum() if "has_anomaly" in merchant_df_sorted.columns else merchant_df_sorted.groupby("date")["is_flagged"].sum() if "is_flagged" in merchant_df_sorted.columns else pd.Series(dtype=float)
        peak_dates = daily_anomalies[daily_anomalies > 0].nlargest(3)
        peak_info = []
        for date, count in peak_dates.items():
            peak_info.append({"date": str(date), "anomaly_count": int(count)})
    else:
        peak_info = []
    
    # Risk factors
    risk_factors = []
    if avg_amount > 5000:
        risk_factors.append("High average transaction amount")
    if len(flagged_txns) / total_txns > 0.1:
        risk_factors.append("High flagged transaction rate (>10%)")
    if len(anomaly_txns) / total_txns > 0.05:
        risk_factors.append("High anomaly rate (>5%)")
    if completed_rate < 0.9:
        risk_factors.append("Low completion rate (<90%)")
    
    # Good factors
    good_factors = []
    if avg_amount < 2000:
        good_factors.append("Low average transaction amount")
    if len(flagged_txns) / total_txns < 0.05:
        good_factors.append("Low flagged transaction rate (<5%)")
    if len(anomaly_txns) / total_txns < 0.02:
        good_factors.append("Low anomaly rate (<2%)")
    if completed_rate > 0.95:
        good_factors.append("High completion rate (>95%)")
    if "loan_limit" in merchant_df.columns:
        avg_loan = merchant_df["loan_limit"].mean() if not merchant_df["loan_limit"].isna().all() else 0
        if avg_loan > 200000:
            good_factors.append("High average loan limits")
    
    analysis["total_txns"] = total_txns
    analysis["flagged_rate"] = len(flagged_txns) / total_txns if total_txns > 0 else 0
    analysis["anomaly_rate"] = len(anomaly_txns) / total_txns if total_txns > 0 else 0
    analysis["avg_amount"] = avg_amount
    analysis["max_amount"] = max_amount
    analysis["min_amount"] = min_amount
    analysis["completed_rate"] = completed_rate
    analysis["risk_factors"] = risk_factors
    analysis["good_factors"] = good_factors
    analysis["peak_dates"] = peak_info
    
    return analysis

# Analyze the selected merchant
merchant_analysis = analyze_merchant_health(dff)

# Display merchant health section
st.subheader("Merchant Health Analysis")

# Risk assessment badge
if merchant_analysis["anomaly_rate"] > 0.05 or merchant_analysis["flagged_rate"] > 0.1:
    st.error("🚩 **High Risk Merchant** - Requires attention")
elif merchant_analysis["anomaly_rate"] > 0.02 or merchant_analysis["flagged_rate"] > 0.05:
    st.warning("⚠️ **Medium Risk Merchant** - Monitor closely")
else:
    st.success("✅ **Low Risk Merchant** - Healthy profile")

# Why this merchant is bad
with st.expander("❌ Why this merchant is considered high risk"):
    if merchant_analysis["risk_factors"]:
        for factor in merchant_analysis["risk_factors"]:
            st.write(f"• {factor}")
    else:
        st.write("No significant risk factors identified for this merchant.")

# Why this merchant is good
with st.expander("✅ Why this merchant is considered low risk"):
    if merchant_analysis["good_factors"]:
        for factor in merchant_analysis["good_factors"]:
            st.write(f"• {factor}")
    else:
        st.write("No particular good factors identified - monitor regularly")

# Peak anomaly dates
st.subheader("📈 Anomaly Peak Detection")
if merchant_analysis["peak_dates"]:
    peak_df = pd.DataFrame(merchant_analysis["peak_dates"])
    fig_peak = px.bar(peak_df, x="date", y="anomaly_count",
                      title="Top 3 Days with Most Anomalies",
                      labels={"anomaly_count": "Anomaly Count", "date": "Date"})
    st.plotly_chart(fig_peak, width='stretch')
    
    st.write("**Peak anomaly dates:**")
    for peak in merchant_analysis["peak_dates"]:
        st.write(f"- {peak['date']}: {peak['anomaly_count']} anomalies detected")
else:
    st.info("No significant anomaly peaks detected for this merchant's transaction period.")

# Summary KPIs
st.subheader("Merchant Summary KPIs")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Transactions", merchant_analysis["total_txns"])
with col2:
    st.metric("Flagged Rate", f"{merchant_analysis['flagged_rate']:.1%}")
with col3:
    st.metric("Anomaly Rate", f"{merchant_analysis['anomaly_rate']:.1%}")
with col4:
    st.metric("Avg Transaction Amount", f"₹{merchant_analysis['avg_amount']:.0f}")

# Trend chart (Plotly interactive)
st.subheader("Transaction Amount Over Time")
chart_df = dff.set_index("timestamp")[["amount"]].sort_index()
fig_amount = px.line(chart_df, x=chart_df.index, y="amount", title="Amount vs Time")
st.plotly_chart(fig_amount, width='stretch')

# Scatter: amount vs score
st.subheader("Amount vs Risk Score")
fig_scatter = px.scatter(dff, x="credit_score", y="amount", color="risk_band",
                         title="Amount vs Risk Score by Band",
                         hover_data=["txn_id", "payer_id"])
st.plotly_chart(fig_scatter, width='stretch')

# Risk band distribution
st.subheader("Risk Band Distribution")
fig_band = px.pie(dff, names="risk_band", title="Risk Band Breakdown",
                  hole=0.4)
st.plotly_chart(fig_band, width='stretch')

# Flagged transactions table
st.subheader("Flagged Transactions")
flagged = dff[dff["is_flagged"] == True] if "is_flagged" in dff.columns else dff.iloc[0:0]
if flagged.empty:
    st.info("No flagged transactions for this merchant.")
else:
    st.dataframe(
        flagged[["txn_id", "payer_id", "amount", "timestamp", "status", "flag_reason"] + (["anomaly_score"] if "anomaly_score" in flagged.columns else [])]
    )

# All transactions (optional, collapsible)
with st.expander("View all transactions for this merchant"):
    st.dataframe(
        dff[["txn_id", "payer_id", "amount", "timestamp", "status"]]
    )