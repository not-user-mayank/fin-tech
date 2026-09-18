"""Generate a small deterministic transaction dataset for the fintech demo."""

from pathlib import Path

import numpy as np
import pandas as pd


RANDOM_SEED = 42
OUTPUT_PATH = Path(__file__).resolve().parent / "data" / "transactions.csv"

N_MERCHANTS = 24
N_PAYERS = 1200
N_BASE_TRANSACTIONS = 3000
N_VELOCITY_PAYERS = 8
N_VELOCITY_TRANSACTIONS = 16
INTERVALS_PER_DAY = 96
DATE_RANGE_DAYS = 90

THRESHOLD_AMOUNTS = np.array([999, 1499, 1999, 2499])


def _normal_amount(rng: np.random.Generator, base: float = 350, scale: float = 180) -> float:
    """Generate a realistic-looking transaction amount (always positive)."""
    return max(1.0, round(float(rng.normal(base, scale)), 2))


def _build_velocity_transactions(
    rng: np.random.Generator,
    merchant_ids: np.ndarray,
    payer_ids: np.ndarray,
    timestamps: pd.DatetimeIndex,
) -> list[dict[str, object]]:
    """Create short bursts of near-threshold transactions for selected payers."""
    rows: list[dict[str, object]] = []

    selected_payers = rng.choice(payer_ids, size=N_VELOCITY_PAYERS, replace=False)
    for payer_id in selected_payers:
        merchant_id = merchant_ids[rng.integers(0, len(merchant_ids))]
        start_index = rng.integers(0, len(timestamps) - N_VELOCITY_TRANSACTIONS)
        burst_start = timestamps[start_index]

        for _ in range(N_VELOCITY_TRANSACTIONS):
            rows.append(
                {
                    "merchant_id": merchant_id,
                    "payer_id": payer_id,
                    "amount": float(rng.choice(THRESHOLD_AMOUNTS)),
                    "timestamp": burst_start + pd.Timedelta(minutes=15),
                    "status": rng.choice(["completed", "failed", "pending"]),
                }
            )

    return rows


def generate_transactions() -> pd.DataFrame:
    """Create the transaction DataFrame used by the dashboard prototype."""
    rng = np.random.default_rng(RANDOM_SEED)

    merchant_ids = np.array([f"M{i:03d}" for i in range(1, N_MERCHANTS + 1)])
    payer_ids = np.array([f"P{i:04d}" for i in range(1, N_PAYERS + 1)])

    # The full timestamp grid lets the velocity bursts fall into a short time window.
    total_rows = N_BASE_TRANSACTIONS + N_VELOCITY_PAYERS * N_VELOCITY_TRANSACTIONS
    timestamps = pd.date_range(
        start="2025-01-01",
        periods=total_rows,
        freq=f"{1440 // INTERVALS_PER_DAY}min",
    )

    merchant_idx = rng.integers(0, len(merchant_ids), size=N_BASE_TRANSACTIONS)
    payer_idx = rng.integers(0, len(payer_ids), size=N_BASE_TRANSACTIONS)

    rows: list[dict[str, object]] = []
    for i in range(N_BASE_TRANSACTIONS):
        rows.append(
            {
                "merchant_id": merchant_ids[merchant_idx[i]],
                "payer_id": payer_ids[payer_idx[i]],
                "amount": _normal_amount(rng),
                "timestamp": timestamps[i],
                "status": rng.choice(["completed", "failed", "pending"]),
            }
        )

    rows.extend(_build_velocity_transactions(rng, merchant_ids, payer_ids, timestamps))

    transactions = pd.DataFrame(rows)
    transactions = transactions.sort_values(["timestamp", "merchant_id", "payer_id"])
    transactions.insert(0, "txn_id", [f"T{i:06d}" for i in range(1, len(transactions) + 1)])

    return transactions


def main() -> None:
    transactions = generate_transactions()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    transactions.to_csv(OUTPUT_PATH, index=False)

    print(f"Wrote {len(transactions):,} transactions to {OUTPUT_PATH}")
    print(f"Merchants: {transactions['merchant_id'].nunique()}")
    print(f"Payers: {transactions['payer_id'].nunique()}")


if __name__ == "__main__":
    main()
