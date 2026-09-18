"""Flag suspicious transactions using simple heuristic rules."""

from typing import Dict

import pandas as pd


THRESHOLD_AMOUNTS = {999, 1499, 1999, 2499}
VELOCITY_COUNT_THRESHOLD = 10
OUTLIER_MULTIPLIER = 3.0


def _flag_threshold_amounts(df: pd.DataFrame) -> pd.Series:
    """Flag amounts that sit exactly on suspicious thresholds."""
    return df["amount"].isin(THRESHOLD_AMOUNTS)


def _flag_high_velocity(df: pd.DataFrame) -> pd.Series:
    """Flag payers with an unusually high transaction count."""
    payer_counts = df.groupby("payer_id")["txn_id"].count()
    velocity = df["payer_id"].map(payer_counts)
    return velocity >= VELOCITY_COUNT_THRESHOLD


def _flag_large_outliers(df: pd.DataFrame) -> pd.Series:
    """Flag transactions whose amount is far above the merchant's median."""
    medians = df.groupby("merchant_id")["amount"].transform("median")
    outlier = df["amount"] > (medians * OUTLIER_MULTIPLIER)
    return outlier


def flag_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Add `is_flagged` and `flag_reason` columns to the input DataFrame.

    Rules (applied in order; the first match wins):
      1. amount in {999, 1499, 1999, 2499} -> "threshold_amount"
      2. payer has >= 10 transactions         -> "high_velocity"
      3. amount > 3x merchant median         -> "large_outlier"
    """
    df = df.copy()

    threshold = _flag_threshold_amounts(df)
    velocity = _flag_high_velocity(df)
    outlier = _flag_large_outliers(df)

    flagged = threshold | velocity | outlier

    reason: pd.Series = pd.Series("", index=df.index, dtype="object")
    reason = reason.mask(threshold, "threshold_amount")
    reason = reason.mask(~threshold & velocity, "high_velocity")
    reason = reason.mask(~threshold & ~velocity & outlier, "large_outlier")

    df["is_flagged"] = flagged
    df["flag_reason"] = reason

    return df


def _explain() -> Dict[str, str]:
    """Return a short description of each rule for debugging."""
    return {
        "threshold_amount": f"amount in {sorted(THRESHOLD_AMOUNTS)}",
        "high_velocity": f"payer transaction count >= {VELOCITY_COUNT_THRESHOLD}",
        "large_outlier": f"amount > {OUTLIER_MULTIPLIER}x merchant median",
    }


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "data/transactions.csv"
    data = pd.read_csv(path, parse_dates=["timestamp"])
    result = flag_transactions(data)

    print("Columns:", list(result.columns))
    print("Flagged rows:", result["is_flagged"].sum())
    print(result[result["is_flagged"]][["txn_id", "amount", "flag_reason"]].head())