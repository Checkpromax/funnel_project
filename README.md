# Fintech — Product Funnel Analyzer

A data analytics project analyzing the user onboarding funnel, with a simulated A/B test on KYC simplification.

## What I built

A full end-to-end analytics pipeline that:
- Simulates 10,000 users moving through the onboarding funnel (App Open → KYC → First Transaction → Repeat Use)
- Runs a controlled A/B experiment testing a simplified KYC flow (Variant B)
- Uses Advanced SQL (SQLite) for cohort and segment analysis
- Builds an interactive Streamlit dashboard with Plotly charts
- Delivers a structured insight memo with product recommendations

## Key findings

| Finding | Insight |
|---------|---------|
| KYC is the biggest drop-off | 55% of users who start KYC don't complete it |
| Top KYC failure reasons | doc_upload_failed (30%) + session_timeout (25%) = fixable with engineering, not redesign |
| Variant B impact | +35% KYC completion, +50% repeat use — all statistically significant (p < 0.05) |
| Best acquisition channel | Referral users retain at 2x the rate of paid social users |

## Tech stack

- **Python** — data simulation, statistical tests
- **Pandas + NumPy** — data manipulation
- **SQLite + SQL** — 5 analytical queries (cohort, segment, drop-reason)
- **Streamlit + Plotly** — interactive dashboard
- **SciPy + statsmodels** — two-proportion z-test for A/B significance

## How to run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Generate data + run SQL analysis
python generate_data.py

# 3. Launch the dashboard
streamlit run dashboard.py
```

## Project structure

```
fintech_funnel_project/
├── generate_data.py    # Data simulation + SQL queries + A/B test
├── dashboard.py        # Streamlit interactive dashboard
├── requirements.txt
└── README.md
```

## Recommendation to the Product team

Ship Variant B's simplified KYC immediately. The data shows:
1. It is statistically significant across all funnel stages
2. The uplift compounds — every extra KYC completion leads to more first transactions and more repeat users
3. The quick wins (doc compression, session extension) can be shipped in 1 sprint and solve 55% of drop-off without a full redesign

---
*Built as an analyst case study for this role. All data is simulated.*
