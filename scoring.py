"""Weighted scorecard: Score = 300 + 600 * weighted_sum of 7 sub-scores (0-1)."""
from typing import Dict, Any
import pandas as pd
import numpy as np

# Weights (must sum to 1.0)
W = {
    "avg_monthly_inflow": 0.25,
    "active_days": 0.20,
    "growth_trend": 0.15,
    "customer_diversity": 0.15,
    "repeat_customer_ratio": 0.10,
    "revenue_stability": 0.10,
    "fraud_cleanliness": 0.05,
}

BASE_LIMIT = 500_000


def _normalize(series, p05=0.05, p95=0.95):
    low = series.quantile(p05)
    high = series.quantile(p95)
    return ((series - low) / (high - low + 1e-9)).clip(0, 1)


def compute_credit_score(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Work on clean transactions only (filter out flagged anomalies)
    if "is_flagged" in df.columns:
        clean = df[~df["is_flagged"]].copy()
    else:
        clean = df.copy()
    clean["date"] = clean["timestamp"].dt.date
    clean["month"] = pd.to_datetime(clean["timestamp"]).dt.to_period("M")

    # --- Per-merchant aggregates from clean txns ---
    # Monthly monthly inflow (sum per merchant-month)
    monthly = clean.groupby(["merchant_id", "month"])["amount"].sum().reset_index()
    monthly.rename(columns={"amount": "monthly_inflow"}, inplace=True)
    avg_inflow = monthly.groupby("merchant_id")["monthly_inflow"].mean().reset_index()
    avg_inflow.rename(columns={"monthly_inflow": "avg_monthly_inflow"}, inplace=True)

    # Active days (distinct dates in clean set) — treat as monthly avg if multi-month
    active = clean.groupby("merchant_id")["date"].nunique().reset_index()
    active.rename(columns={"date": "active_days_total"}, inplace=True)
    # Approx active-days sub-score: normalize total unique days / 90 (max window)
    active["active_days_sub"] = (active["active_days_total"] / 90.0).clip(0, 1)

    # Growth trend: slope of monthly inflow (positive = good)
    def _growth_rate(group):
        s = group.sort_values("month")
        if len(s) < 2:
            return 0.0
        y = s["monthly_inflow"].values
        x = np.arange(len(y))
        # simple linear slope normalized by mean
        slope = np.polyfit(x, y, 1)[0] if len(y) > 1 else 0.0
        mean_y = y.mean() if y.mean() > 0 else 1
        return float(slope / mean_y)
    growth = (
        monthly.groupby("merchant_id").apply(lambda g: _growth_rate(g)).reset_index(name="growth_rate")
    )
    growth["growth_sub"] = (growth["growth_rate"] / (growth["growth_rate"].abs().max() + 1e-9)).clip(-1, 1)
    growth["growth_sub"] = ((growth["growth_sub"] + 1) / 2).clip(0, 1)  # normalize -1..1 -> 0..1

    # Customer diversity (unique payers / total clean txns — more diversity = higher sub-score)
    diversity = clean.groupby("merchant_id").agg(
        unique_payers=("payer_id", "nunique"),
        total_txns=("txn_id", "count"),
    ).reset_index()
    diversity["diversity_sub"] = (diversity["unique_payers"] / diversity["total_txns"].clip(lower=1)).clip(0, 1)

    # Repeat-customer ratio (payers with >1 clean txn / total unique payers)
    payer_counts = clean.groupby(["merchant_id", "payer_id"]).size().reset_index(name="txns")
    repeat = payer_counts.groupby("merchant_id").apply(lambda g: (g["txns"] > 1).sum() / g["txns"].count()).reset_index(name="repeat_sub")
    repeat["repeat_sub"] = repeat["repeat_sub"].clip(0, 1)

    # Revenue stability (inverse coefficient of variation of monthly inflow)
    monthly_cv = monthly.groupby("merchant_id")["monthly_inflow"].agg(["mean", "std"]).reset_index()
    monthly_cv["std"] = monthly_cv["std"].fillna(0)
    monthly_cv["cv"] = monthly_cv["std"] / monthly_cv["mean"].clip(lower=1)
    monthly_cv["stability_sub"] = (1 - monthly_cv["cv"].clip(0, 2)).clip(0, 1)

    # Fraud cleanliness (1 - flagged ratio among all txns for merchant)
    # If is_flagged exists, use it; else assume 0 flagged
    if "is_flagged" in df.columns:
        fraud = df.groupby("merchant_id").agg(
            total=("txn_id", "count"),
            flagged=("is_flagged", lambda s: int(s.sum()) if s.dtype == bool or s.dtype == object else 0),
        ).reset_index()
    else:
        fraud = df.groupby("merchant_id").agg(total=("txn_id", "count")).reset_index()
        fraud["flagged"] = 0
    fraud["flagged"] = fraud["flagged"].fillna(0).astype(int)
    fraud["fraud_sub"] = (1 - (fraud["flagged"] / fraud["total"].clip(lower=1))).clip(0, 1)

    # Merge all sub-scores
    stats = avg_inflow.merge(active[["merchant_id", "active_days_sub"]], on="merchant_id", how="left")
    stats = stats.merge(growth[["merchant_id", "growth_sub"]], on="merchant_id", how="left")
    stats = stats.merge(diversity[["merchant_id", "diversity_sub"]], on="merchant_id", how="left")
    stats = stats.merge(repeat[["merchant_id", "repeat_sub"]], on="merchant_id", how="left")
    stats = stats.merge(monthly_cv[["merchant_id", "stability_sub"]], on="merchant_id", how="left")
    stats = stats.merge(fraud[["merchant_id", "fraud_sub"]], on="merchant_id", how="left")

    # Fill missing sub-scores with 0.5 (neutral for new merchants / limited data)
    sub_cols = ["avg_monthly_inflow", "active_days_sub", "growth_sub",
                "diversity_sub", "repeat_sub", "stability_sub", "fraud_sub"]
    # We actually need to normalize avg_monthly_inflow to 0..1; do min-max
    stats["avg_monthly_inflow_sub"] = _normalize(stats["avg_monthly_inflow"], p05=0.05, p95=0.95)

    # Weighted sum (0-1)
    stats["weighted_sum"] = (
        W["avg_monthly_inflow"] * stats["avg_monthly_inflow_sub"] +
        W["active_days"] * stats["active_days_sub"].fillna(0.5) +
        W["growth_trend"] * stats["growth_sub"].fillna(0.5) +
        W["customer_diversity"] * stats["diversity_sub"].fillna(0.5) +
        W["repeat_customer_ratio"] * stats["repeat_sub"].fillna(0.5) +
        W["revenue_stability"] * stats["stability_sub"].fillna(0.5) +
        W["fraud_cleanliness"] * stats["fraud_sub"].fillna(0.5)
    )
    stats["weighted_sum"] = stats["weighted_sum"].clip(0, 1)

    # Scale to 300-900
    stats["credit_score"] = (300 + 600 * stats["weighted_sum"]).round(0).astype(int)
    stats["credit_score"] = stats["credit_score"].clip(300, 900)

    # Risk band based on spec mapping
    def _band(s):
        if s >= 750: return "low"
        elif s >= 650: return "moderate"
        elif s >= 550: return "high"
        else: return "decline"
    stats["risk_band"] = stats["credit_score"].apply(_band)

    # Loan limit: multiple of average clean monthly inflow by band
    def _loan_limit(row):
        clean_avg = row["avg_monthly_inflow"] if pd.notna(row["avg_monthly_inflow"]) else 0
        band = row["risk_band"]
        mult = {"low": 2.0, "moderate": 1.0, "high": 0.5, "decline": 0.2}.get(band, 0.5)
        return int(round(clean_avg * mult, 0))
    stats["loan_limit"] = stats.apply(_loan_limit, axis=1)

    # Cold-start cap: fewer than ~20 clean transactions → cap score at 650 (moderate max)
    # Use clean txn count from fraud calculation (total - flagged)
    stats = stats.merge(fraud[["merchant_id", "total"]].rename(columns={"total": "total_all"}), on="merchant_id", how="left")
    # Actually fraud already has total; just compute clean count = total - flagged
    stats["clean_txns"] = stats.get("total_all", stats.get("total", 0)) - stats.get("flagged", 0)
    # Simple cap: if clean_txns < 30, cap at 650
    stats["credit_score"] = stats.apply(
        lambda row: min(row["credit_score"], 650) if (row["clean_txns"] if pd.notna(row.get("clean_txns")) else 0) < 30 else row["credit_score"], axis=1
    )

    # Feature contributions (explainability) — contribution points = sub_score * weight * 600
    def _contributions(row):
        contrib = {}
        # Sub-score values for reporting (0-1)
        contrib["avg_monthly_inflow_sub"] = round(row["avg_monthly_inflow_sub"], 2)
        contrib["active_days_sub"] = round(row["active_days_sub"], 2)
        contrib["growth_trend_sub"] = round(row["growth_sub"], 2)
        contrib["customer_diversity_sub"] = round(row["diversity_sub"], 2)
        contrib["repeat_customer_sub"] = round(row["repeat_sub"], 2)
        contrib["revenue_stability_sub"] = round(row["stability_sub"], 2)
        contrib["fraud_cleanliness_sub"] = round(row["fraud_sub"], 2)
        # Points contribution = weight * sub * 600 (since score = 300 + 600*weighted)
        contrib["points_avg_inflow"] = round(W["avg_monthly_inflow"] * row["avg_monthly_inflow_sub"] * 600, 0)
        contrib["points_active_days"] = round(W["active_days"] * row["active_days_sub"] * 600, 0)
        contrib["points_growth"] = round(W["growth_trend"] * row["growth_sub"] * 600, 0)
        contrib["points_diversity"] = round(W["customer_diversity"] * row["diversity_sub"] * 600, 0)
        contrib["points_repeat"] = round(W["repeat_customer_ratio"] * row["repeat_sub"] * 600, 0)
        contrib["points_stability"] = round(W["revenue_stability"] * (row.get("stability_sub") or 0) * 600, 0)
        contrib["points_fraud_clean"] = round(W["fraud_cleanliness"] * row["fraud_sub"] * 600, 0)
        # Human-readable explanation for dashboard
        parts = [
            f"Inflow: +{int(contrib['points_avg_inflow'])} pts",
            f"Active days: +{int(contrib['points_active_days'])} pts",
            f"Growth: +{int(contrib['points_growth'])} pts",
            f"Diversity: +{int(contrib['points_diversity'])} pts",
            f"Repeat: +{int(contrib['points_repeat'])} pts",
            f"Stability: +{int(contrib['points_stability'])} pts",
            f"Fraud clean: +{int(contrib['points_fraud_clean'])} pts",
        ]
        contrib["explanation"] = "; ".join(parts)
        return contrib

    stats["feature_contributions"] = stats.apply(_contributions, axis=1)

    # Final merge back to transaction-level dataframe for dashboard consumption
    df = df.merge(
        stats[[
            "merchant_id", "credit_score", "risk_band", "loan_limit",
            "weighted_sum", "feature_contributions",
        ]],
        on="merchant_id",
        how="left",
    )
    return df


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "data/transactions.csv"
    data = pd.read_csv(path, parse_dates=["timestamp"])
    result = compute_credit_score(data)
    print("New columns:", [c for c in result.columns if c not in data.columns])
    print()
    summary = result[["merchant_id", "credit_score", "risk_band", "loan_limit", "weighted_sum"]].drop_duplicates()
    print(summary.sort_values("credit_score", ascending=False).head().to_string(index=False))
