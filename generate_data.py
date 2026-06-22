"""
Product Funnel Analyzer
generate_data.py — Simulate user funnel data + A/B test experiment

Funnel: App Open → KYC Started → KYC Completed → First Transaction → Repeat Use
"""

import pandas as pd
import numpy as np
import sqlite3
import os

np.random.seed(42)

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
N_USERS = 10_000
DB_PATH = "fintech_funnel.db"

# Funnel drop-off rates (control group — current product)
CONTROL_RATES = {
    "app_open":           1.00,
    "kyc_started":        0.72,   # 28% bounce before starting KYC
    "kyc_completed":      0.45,   # big pain point — identity verification friction
    "first_transaction":  0.38,
    "repeat_use":         0.22,
}

# Variant B: simplified KYC (fewer steps, better UX)
# Only KYC stages improve; rest stays same
VARIANT_RATES = {
    "app_open":           1.00,
    "kyc_started":        0.79,   # better onboarding nudge
    "kyc_completed":      0.61,   # simplified KYC — fewer doc uploads
    "first_transaction":  0.52,
    "repeat_use":         0.33,
}

CITIES = ["Bengaluru", "Mumbai", "Delhi", "Hyderabad", "Chennai", "Pune", "Kolkata"]
CITY_WEIGHTS = [0.22, 0.20, 0.18, 0.13, 0.11, 0.10, 0.06]

AGE_GROUPS = ["18-24", "25-30", "31-40", "41+"]
AGE_WEIGHTS = [0.35, 0.30, 0.25, 0.10]

ACQUISITION = ["organic", "referral", "paid_social", "influencer", "email"]
ACQ_WEIGHTS  = [0.30, 0.25, 0.20, 0.15, 0.10]


# ─────────────────────────────────────────────
# SIMULATE FUNNEL DATA
# ─────────────────────────────────────────────
def simulate_users(n, variant, rates):
    users = []
    for i in range(n):
        city        = np.random.choice(CITIES, p=CITY_WEIGHTS)
        age_group   = np.random.choice(AGE_GROUPS, p=AGE_WEIGHTS)
        acquisition = np.random.choice(ACQUISITION, p=ACQ_WEIGHTS)

        # Roll through each funnel step
        app_open          = 1
        kyc_started       = int(np.random.rand() < rates["kyc_started"])
        kyc_completed     = int(kyc_started and np.random.rand() < (rates["kyc_completed"] / rates["kyc_started"]))
        first_transaction = int(kyc_completed and np.random.rand() < (rates["first_transaction"] / rates["kyc_completed"]))
        repeat_use        = int(first_transaction and np.random.rand() < (rates["repeat_use"] / rates["first_transaction"]))

        # Simulate KYC drop reason for diagnostic analysis
        kyc_drop_reason = None
        if kyc_started and not kyc_completed:
            kyc_drop_reason = np.random.choice(
                ["doc_upload_failed", "session_timeout", "selfie_mismatch", "user_abandoned"],
                p=[0.30, 0.25, 0.25, 0.20]
            )

        users.append({
            "user_id":           f"{variant[0]}{i:06d}",
            "variant":           variant,
            "city":              city,
            "age_group":         age_group,
            "acquisition":       acquisition,
            "app_open":          app_open,
            "kyc_started":       kyc_started,
            "kyc_completed":     kyc_completed,
            "first_transaction": first_transaction,
            "repeat_use":        repeat_use,
            "kyc_drop_reason":   kyc_drop_reason,
        })
    return users


def build_dataset():
    half = N_USERS // 2
    control = simulate_users(half, "control", CONTROL_RATES)
    variant = simulate_users(half, "variant_b", VARIANT_RATES)
    df = pd.DataFrame(control + variant)
    return df


# ─────────────────────────────────────────────
# SAVE TO SQLITE
# ─────────────────────────────────────────────
def save_to_db(df):
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    df.to_sql("funnel_events", conn, index=False)
    conn.close()
    print(f"✓ Saved {len(df):,} users to {DB_PATH}")


# ─────────────────────────────────────────────
# SQL ANALYSIS QUERIES
# ─────────────────────────────────────────────
QUERIES = {
    "1_overall_funnel_by_variant": """
        SELECT
            variant,
            COUNT(*)                                     AS total_users,
            ROUND(AVG(kyc_started)     * 100, 1)        AS pct_kyc_started,
            ROUND(AVG(kyc_completed)   * 100, 1)        AS pct_kyc_completed,
            ROUND(AVG(first_transaction) * 100, 1)      AS pct_first_txn,
            ROUND(AVG(repeat_use)      * 100, 1)        AS pct_repeat_use
        FROM funnel_events
        GROUP BY variant
    """,

    "2_kyc_drop_reasons": """
        SELECT
            variant,
            kyc_drop_reason,
            COUNT(*) AS users_dropped,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY variant), 1) AS pct_of_drops
        FROM funnel_events
        WHERE kyc_started = 1 AND kyc_completed = 0
        GROUP BY variant, kyc_drop_reason
        ORDER BY variant, users_dropped DESC
    """,

    "3_funnel_by_city": """
        SELECT
            city,
            COUNT(*)                                   AS users,
            ROUND(AVG(kyc_completed)   * 100, 1)      AS kyc_completion_pct,
            ROUND(AVG(first_transaction) * 100, 1)    AS first_txn_pct,
            ROUND(AVG(repeat_use)      * 100, 1)      AS repeat_use_pct
        FROM funnel_events
        GROUP BY city
        ORDER BY repeat_use_pct DESC
    """,

    "4_funnel_by_age_group": """
        SELECT
            age_group,
            variant,
            COUNT(*)                                   AS users,
            ROUND(AVG(kyc_completed)   * 100, 1)      AS kyc_pct,
            ROUND(AVG(repeat_use)      * 100, 1)      AS repeat_pct
        FROM funnel_events
        GROUP BY age_group, variant
        ORDER BY age_group, variant
    """,

    "5_acquisition_to_retention": """
        SELECT
            acquisition,
            COUNT(*)                                   AS total,
            ROUND(AVG(kyc_completed)   * 100, 1)      AS kyc_pct,
            ROUND(AVG(repeat_use)      * 100, 1)      AS retention_pct,
            ROUND(AVG(repeat_use) / NULLIF(AVG(kyc_completed), 0) * 100, 1) AS post_kyc_retention
        FROM funnel_events
        GROUP BY acquisition
        ORDER BY retention_pct DESC
    """,
}


def run_queries():
    conn = sqlite3.connect(DB_PATH)
    results = {}
    for name, sql in QUERIES.items():
        df = pd.read_sql_query(sql, conn)
        results[name] = df
        print(f"\n── Query: {name} ──")
        print(df.to_string(index=False))
    conn.close()
    return results


# ─────────────────────────────────────────────
# A/B TEST STATISTICAL SIGNIFICANCE
# ─────────────────────────────────────────────
from scipy import stats

def ab_significance_test(df):
    print("\n── A/B Test: Statistical Significance ──")
    metrics = ["kyc_completed", "first_transaction", "repeat_use"]
    ctrl = df[df["variant"] == "control"]
    var  = df[df["variant"] == "variant_b"]

    for metric in metrics:
        n_ctrl = len(ctrl)
        n_var  = len(var)
        p_ctrl = ctrl[metric].mean()
        p_var  = var[metric].mean()

        # Two-proportion z-test
        count = [ctrl[metric].sum(), var[metric].sum()]
        nobs  = [n_ctrl, n_var]
        from statsmodels.stats.proportion import proportions_ztest
        z_stat, p_value = proportions_ztest(count, nobs)

        uplift = (p_var - p_ctrl) / p_ctrl * 100
        sig    = "✓ Significant" if p_value < 0.05 else "✗ Not significant"

        print(f"  {metric:20s}  control={p_ctrl:.1%}  variant={p_var:.1%}  "
              f"uplift={uplift:+.1f}%  p={p_value:.4f}  {sig}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("── Generating funnel data ──")
    df = build_dataset()
    print(f"  Total users: {len(df):,}  |  Control: {len(df[df.variant=='control']):,}  |  Variant B: {len(df[df.variant=='variant_b']):,}")

    save_to_db(df)
    run_queries()
    ab_significance_test(df)

    # Save CSV for dashboard
    df.to_csv("funnel_data.csv", index=False)
    print("\n✓ funnel_data.csv saved — ready for Streamlit dashboard")
    print("  Run: streamlit run dashboard.py")
