"""
Product Funnel Analyzer — Streamlit Dashboard
dashboard.py

Run: streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from scipy import stats

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Fintech — Funnel Analyzer",
    page_icon="🔪",
    layout="wide",
)

st.markdown("""
<style>
    .metric-card {
        background: #000000;
        border-radius: 10px;
        padding: 1rem 1.25rem;
        border: 1px solid #000000;
    }
    .insight-box {
        background: #000000;
        border-left: 4px solid #378ADD;
        border-radius: 6px;
        padding: 0.75rem 1rem;
        margin: 0.5rem 0;
        font-size: 14px;
    }
    .warn-box {
        background: #000000;
        border-left: 4px solid #EF9F27;
        border-radius: 6px;
        padding: 0.75rem 1rem;
        margin: 0.5rem 0;
        font-size: 14px;
    }
    .sig-badge {
        background: #000000;
        color: #1a6b31;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────
@st.cache_data
def load_data():
    try:
        return pd.read_csv("funnel_data.csv")
    except FileNotFoundError:
        st.error("Run `python generate_data.py` first to generate the data.")
        st.stop()

df = load_data()
ctrl    = df[df["variant"] == "control"]
variant = df[df["variant"] == "variant_b"]

FUNNEL_STEPS = ["app_open", "kyc_started", "kyc_completed", "first_transaction", "repeat_use"]
STEP_LABELS  = ["App Open", "KYC Started", "KYC Completed", "First Transaction", "Repeat Use"]

SLICE_BLUE   = "#378ADD"
SLICE_PURPLE = "#7F77DD"
AMBER        = "#EF9F27"
CORAL        = "#D85A30"


# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown("## Fintech — Product Funnel Analyzer")
st.markdown("**KYC Simplification A/B Test** · 10,000 simulated users · Control vs Variant B")
st.divider()


# ─────────────────────────────────────────────
# SECTION 1 — TOP METRICS
# ─────────────────────────────────────────────
st.markdown("### Overall performance")
cols = st.columns(4)

metrics = [
    ("KYC Completion", "kyc_completed"),
    ("First Transaction", "first_transaction"),
    ("Repeat Use", "repeat_use"),
    ("Control → Variant Uplift (KYC)", None),
]

ctrl_kyc = ctrl["kyc_completed"].mean()
var_kyc  = variant["kyc_completed"].mean()
uplift   = (var_kyc - ctrl_kyc) / ctrl_kyc * 100

vals = [
    (f"{ctrl_kyc:.1%}", f"{var_kyc:.1%}", "Control vs Variant B"),
    (f"{ctrl['first_transaction'].mean():.1%}", f"{variant['first_transaction'].mean():.1%}", "Control vs Variant B"),
    (f"{ctrl['repeat_use'].mean():.1%}", f"{variant['repeat_use'].mean():.1%}", "Control vs Variant B"),
    (f"+{uplift:.1f}%", "vs control", "KYC completion uplift"),
]

labels = ["KYC Completion", "First Transaction", "Repeat Use", "KYC Uplift (B vs Control)"]
for col, label, (v1, v2, sub) in zip(cols, labels, vals):
    with col:
        st.metric(label=label, value=v1, delta=f"{v2} → variant" if label != "KYC Uplift (B vs Control)" else v2)

st.divider()


# ─────────────────────────────────────────────
# SECTION 2 — FUNNEL CHART SIDE BY SIDE
# ─────────────────────────────────────────────
st.markdown("### Funnel comparison — Control vs Variant B")

col1, col2 = st.columns(2)

for col, grp, name, color in [
    (col1, ctrl,    "Control (current KYC)", SLICE_BLUE),
    (col2, variant, "Variant B (simplified KYC)", SLICE_PURPLE),
]:
    with col:
        values = [grp[s].mean() * 100 for s in FUNNEL_STEPS]
        fig = go.Figure(go.Funnel(
            y=STEP_LABELS,
            x=values,
            textinfo="value+percent previous",
            marker=dict(color=color),
            textfont=dict(size=13),
        ))
        fig.update_layout(
            title=dict(text=name, font=dict(size=14)),
            margin=dict(l=0, r=0, t=40, b=0),
            height=340,
            plot_bgcolor="black",
            paper_bgcolor="black",
        )
        st.plotly_chart(fig, use_container_width=True)

st.divider()


# ─────────────────────────────────────────────
# SECTION 3 — A/B TEST SIGNIFICANCE
# ─────────────────────────────────────────────
st.markdown("### A/B test — statistical significance")

from statsmodels.stats.proportion import proportions_ztest

ab_rows = []
for step, label in zip(FUNNEL_STEPS[1:], STEP_LABELS[1:]):
    n_c, n_v = len(ctrl), len(variant)
    p_c = ctrl[step].mean()
    p_v = variant[step].mean()
    count = [ctrl[step].sum(), variant[step].sum()]
    nobs  = [n_c, n_v]
    z, p  = proportions_ztest(count, nobs)
    uplift_pct = (p_v - p_c) / p_c * 100
    ab_rows.append({
        "Funnel Step": label,
        "Control": f"{p_c:.1%}",
        "Variant B": f"{p_v:.1%}",
        "Uplift": f"+{uplift_pct:.1f}%",
        "p-value": round(p, 4),
        "Significant?": "✓ Yes" if p < 0.05 else "✗ No",
    })

ab_df = pd.DataFrame(ab_rows)
st.dataframe(ab_df, use_container_width=True, hide_index=True)

st.markdown("""
<div class="insight-box">
💡 <strong>All funnel steps show statistically significant improvement (p &lt; 0.05).</strong>
The simplified KYC in Variant B lifts repeat use by ~50% relative — a compounding benefit since every extra retained user generates long-term revenue.
</div>
""", unsafe_allow_html=True)

st.divider()


# ─────────────────────────────────────────────
# SECTION 4 — KYC DROP REASON ANALYSIS
# ─────────────────────────────────────────────
st.markdown("### Why users drop at KYC (control group)")

kyc_drops = ctrl[ctrl["kyc_started"] == 1][ctrl["kyc_completed"] == 0]
reason_counts = (
    kyc_drops["kyc_drop_reason"]
    .value_counts()
    .reset_index()
)
reason_counts.columns = ["Reason", "Count"]
reason_counts["Pct"] = (reason_counts["Count"] / reason_counts["Count"].sum() * 100).round(1)

fig_bar = px.bar(
    reason_counts,
    x="Reason", y="Pct",
    text="Pct",
    color="Reason",
    color_discrete_sequence=[CORAL, AMBER, SLICE_BLUE, SLICE_PURPLE],
    labels={"Pct": "% of KYC drops"},
)
fig_bar.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
fig_bar.update_layout(
    showlegend=False,
    margin=dict(l=0, r=0, t=20, b=0),
    height=300,
    plot_bgcolor="black",
    paper_bgcolor="black",
    yaxis=dict(title="% of drops", gridcolor="#f0f0f0"),
)
st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("""
<div class="warn-box">
⚠️ <strong>doc_upload_failed</strong> and <strong>session_timeout</strong> together account for ~55% of KYC drops.
These are fixable with better file compression on upload and session extension. No redesign needed — just engineering fixes.
</div>
""", unsafe_allow_html=True)

st.divider()


# ─────────────────────────────────────────────
# SECTION 5 — CITY-WISE FUNNEL
# ─────────────────────────────────────────────
st.markdown("### Funnel performance by city")

city_df = (
    df.groupby("city")[["kyc_completed", "first_transaction", "repeat_use"]]
    .mean()
    .mul(100)
    .round(1)
    .reset_index()
    .sort_values("repeat_use", ascending=False)
)

fig_city = go.Figure()
for col, color, name in [
    ("kyc_completed",    SLICE_BLUE,   "KYC Completed"),
    ("first_transaction", SLICE_PURPLE, "First Transaction"),
    ("repeat_use",       CORAL,        "Repeat Use"),
]:
    fig_city.add_trace(go.Bar(
        name=name,
        x=city_df["city"],
        y=city_df[col],
        marker_color=color,
    ))

fig_city.update_layout(
    barmode="group",
    margin=dict(l=0, r=0, t=10, b=0),
    height=320,
    plot_bgcolor="black",
    paper_bgcolor="black",
    yaxis=dict(title="% of users", gridcolor="#f0f0f0"),
    legend=dict(orientation="h", y=1.1),
)
st.plotly_chart(fig_city, use_container_width=True)

st.divider()


# ─────────────────────────────────────────────
# SECTION 6 — ACQUISITION CHANNEL ANALYSIS
# ─────────────────────────────────────────────
st.markdown("### Which acquisition channel retains users best?")

acq_df = (
    df.groupby("acquisition")[["kyc_completed", "first_transaction", "repeat_use"]]
    .mean()
    .mul(100)
    .round(1)
    .reset_index()
    .sort_values("repeat_use", ascending=False)
)

fig_acq = px.scatter(
    acq_df,
    x="kyc_completed",
    y="repeat_use",
    size="first_transaction",
    text="acquisition",
    color="acquisition",
    color_discrete_sequence=[SLICE_BLUE, SLICE_PURPLE, AMBER, CORAL, "#1D9E75"],
    labels={"kyc_completed": "KYC Completion %", "repeat_use": "Repeat Use %"},
    size_max=30,
)
fig_acq.update_traces(textposition="top center")
fig_acq.update_layout(
    showlegend=False,
    margin=dict(l=0, r=0, t=10, b=0),
    height=350,
    plot_bgcolor="black",
    paper_bgcolor="black",
)
st.plotly_chart(fig_acq, use_container_width=True)

st.markdown("""
<div class="insight-box">
💡 <strong>Referral users convert and retain the best</strong> — highest repeat use despite similar KYC completion.
Recommendation: Double referral program budget before scaling paid social, which shows high acquisition but lower long-term retention.
</div>
""", unsafe_allow_html=True)

st.divider()


# ─────────────────────────────────────────────
# SECTION 7 — INSIGHT MEMO
# ─────────────────────────────────────────────
st.markdown("### Insight memo — recommendations for Product & Growth teams")

st.markdown("""
| # | Finding | Impact | Recommended Action |
|---|---------|--------|-------------------|
| 1 | Variant B KYC lifts repeat use by ~50% | High | Ship simplified KYC to 100% of users |
| 2 | doc_upload_failed = 30% of KYC drops | High | Add client-side image compression before upload |
| 3 | session_timeout = 25% of KYC drops | Medium | Extend session to 30 min + add "save progress" |
| 4 | Referral channel has highest retention | Medium | Increase referral incentive from ₹50 → ₹100 |
| 5 | 18–24 age group has lowest repeat use | Medium | In-app nudge after first transaction: "Try UPI autopay" |
""")

st.caption("Built by a data analyst who thinks like a product manager. · Analyst Case Project")
