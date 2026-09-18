"""Compute per-merchant risk score, band, loan limit, and feature contributions."""

from typing import Dict

import pandas as pd

BASE_LIMIT = 500_000


def compute_score(df: pd.DataFrame) -> pd.DataFrame:
    """Add per-merchant score, risk_band, loan_limit, feature_contributions.

    Uses simple features:
      - total_inflow (sum of amounts)
      - active_days (distinct date from timestamp)
      - avg_transaction_size
      - fail_pending_ratio (failed + pending / total)

    Score (0-100) weights:
      - total_inflow 30%
      - active_days 20%
      - avg_size 20%
      - low_fail_ratio 30% (higher score = lower failure rate)
    """
    df = df.copy()
    df["date"] = df["timestamp"].dt.date

    # Per-merchant features
    merchant_stats = (
        df.groupby("merchant_id")
        .agg(
            total_inflow=("amount", "sum"),
            active_days=("date", "nunique"),
            avg_amount=("amount", "mean"),
            total_txns=("txn_id", "count"),
            fail_pending=("status", lambda s: s.isin(["failed", "pending"]).sum()),
        )
        .reset_index()
    )

    merchant_stats["fail_pending_ratio"] = merchant_stats["fail_pending"] / merchant_stats["total_txns"]

    # Normalize each feature to ~0-100 (simple min-max using percentiles to avoid extreme skew)
    for col in ["total_inflow", "active_days", "avg_amount"]:
        p05 = merchant_stats[col].quantile(0.05)
        p95 = merchant_stats[col].quantile(0.95)
        merchant_stats[col + "_norm"] = ((merchant_stats[col] - p05) / (p95 - p05 + 1e-9)).clip(0, 1) * 100

    merchant_stats["fail_ratio_norm"] = (1 - merchant_stats["fail_pending_ratio"].clip(0, 1)) * 100

    # Weighted score
    merchant_stats["score"] = (
        0.30 * merchant_stats["total_inflow_norm"]
        + 0.20 * merchant_stats["active_days_norm"]
        + 0.20 * merchant_stats["avg_amount_norm"]
        + 0.30 * merchant_stats["fail_ratio_norm"]
    ).round(1)

    merchant_stats["score"] = merchant_stats["score"].clip(0, 100).round(1)

    # Risk band
    def band(score):
        if score >= 70:
            return "low"
        elif score >= 40:
            return "medium"
        else:
            return "high"

    merchant_stats["risk_band"] = merchant_stats["score"].apply(band)

    merchant_stats["loan_limit"] = (BASE_LIMIT * (1 + merchant_stats["score"] / 100)).round(0).astype(int)

    # Feature contributions (simple string explanation)
    def contributions(row):
        return {
            "total_inflow": f"INR {row['total_inflow']:,.0f}",
            "active_days": int(row["active_days"]),
            "avg_amount": f"INR {row['avg_amount']:,.2f}",
            "fail_pending_ratio": f"{row['fail_pending_ratio']:.2%}",
            "primary_driver": (
                "volume" if row["total_inflow_norm"] > 70 else
                "activity" if row["active_days_norm"] > 70 else
                "reliability" if row["fail_ratio_norm"] > 70 else "mixed"
            ),
        }

    merchant_stats["feature_contributions"] = merchant_stats.apply(contributions, axis=1)

    # Merge back to every row
    df = df.merge(
        merchant_stats[["merchant_id", "score", "risk_band", "loan_limit", "feature_contributions"]],
        on="merchant_id",
        how="left",
    )

    # Drop helper date column
    df = df.drop(columns=["date"])

    return df


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "data/transactions.csv"
    data = pd.read_csv(path, parse_dates=["timestamp"])
    result = compute_score(data)

    print("New columns:", [c for c in result.columns if c not in data.columns])
    print()
    print("Per-merchant unique values (first 5):")
    print(
        result[["merchant_id", "score", "risk_band", "loan_limit"]]
        .drop_duplicates()
        .sort_values("score", ascending=False)
        .head()
        .to_string(index=False)
    )