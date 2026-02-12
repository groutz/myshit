"""
Pipeline Page
Project pipeline management with scoring, forecasting, and director capacity planning.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date

import database as db

db.init_db()

st.set_page_config(page_title="Pipeline - Survey Agency PM", layout="wide")
st.title("Project Pipeline & Forecasting")

today = date.today()

# ===================================================================
# PIPELINE TABLE
# ===================================================================
st.subheader("Pipeline Projects")

pipeline = db.get_pipeline_summary()

if not pipeline:
    st.info("No pipeline projects. Add projects with 'Pipeline' status on the Projects page.")
    st.stop()

# Build display data with composite score
rows = []
for p in pipeline:
    # Composite pipeline score (weighted formula)
    # Weight: Likelihood 35%, Margin 25%, Reputation 20%, Exports 10%, Value 10%
    value_score = min(p["contract_value"] / 150000 * 5, 5)  # Normalize to 0-5 scale
    composite = (
        (p["likelihood_pct"] / 100 * 5) * 0.35 +
        (max(0, p["expected_margin_pct"]) / 50 * 5) * 0.25 +
        p["reputation_score"] * 0.20 +
        (5 if p["exports_oriented"] else 2) * 0.10 +
        value_score * 0.10
    )

    rows.append({
        "Project": p["name"],
        "Client": p["client"],
        "Method": p["implementation_method"],
        "Contract Value": p["contract_value"],
        "Likelihood": p["likelihood_pct"],
        "Weighted Value": p["weighted_value"],
        "Expected Margin %": p["expected_margin_pct"],
        "Weighted Profit": p["weighted_profit"],
        "Reputation": p["reputation_score"],
        "Exports": "Yes" if p["exports_oriented"] else "No",
        "Director Inv. %": p["director_involvement_pct"],
        "Duration (mo)": p["expected_duration_months"],
        "Exp. Start": p["expected_start_date"],
        "Score": round(composite, 2),
    })

df_pipeline = pd.DataFrame(rows).sort_values("Score", ascending=False)

st.dataframe(
    df_pipeline.style.format({
        "Contract Value": "{:,.0f}",
        "Likelihood": "{:.0f}%",
        "Weighted Value": "{:,.0f}",
        "Expected Margin %": "{:.0f}%",
        "Weighted Profit": "{:,.0f}",
        "Director Inv. %": "{:.0f}%",
        "Score": "{:.2f}",
    }).background_gradient(subset=["Score"], cmap="RdYlGn"),
    use_container_width=True,
    hide_index=True,
)

# --- Pipeline KPIs ---
st.divider()
total_pipeline = sum(r["Contract Value"] for r in rows)
total_weighted = sum(r["Weighted Value"] for r in rows)
total_weighted_profit = sum(r["Weighted Profit"] for r in rows)
avg_likelihood = sum(r["Likelihood"] for r in rows) / len(rows) if rows else 0
avg_margin = sum(r["Expected Margin %"] for r in rows) / len(rows) if rows else 0

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Pipeline Value", f"{total_pipeline:,.0f}")
k2.metric("Weighted Value", f"{total_weighted:,.0f}")
k3.metric("Weighted Profit", f"{total_weighted_profit:,.0f}")
k4.metric("Avg Likelihood", f"{avg_likelihood:.0f}%")
k5.metric("Avg Expected Margin", f"{avg_margin:.0f}%")

# ===================================================================
# PIPELINE VISUALIZATIONS
# ===================================================================
st.divider()
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Pipeline by Likelihood")
    fig = px.scatter(
        df_pipeline,
        x="Likelihood",
        y="Contract Value",
        size="Weighted Value",
        color="Method",
        hover_name="Project",
        text="Project",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_traces(textposition="top center", textfont_size=9)
    fig.update_layout(
        height=400,
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis_title="Likelihood of Winning (%)",
        yaxis_title="Contract Value",
    )
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("Pipeline by Implementation Method")
    method_summary = df_pipeline.groupby("Method").agg(
        Projects=("Project", "count"),
        Total_Value=("Contract Value", "sum"),
        Weighted_Value=("Weighted Value", "sum"),
    ).reset_index()

    fig = px.bar(
        method_summary,
        x="Method",
        y=["Total_Value", "Weighted_Value"],
        barmode="group",
        labels={"value": "Value", "variable": "Type"},
        color_discrete_map={"Total_Value": "#aec7e8", "Weighted_Value": "#1f77b4"},
    )
    fig.update_layout(height=400, margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(fig, use_container_width=True)

# ===================================================================
# MONTHLY REVENUE FORECAST
# ===================================================================
st.divider()
st.subheader("Monthly Revenue & Profit Forecast")
st.caption("Based on all active and pipeline projects, weighted by likelihood of winning.")

col_fy, col_fm = st.columns([1, 4])
forecast_year = col_fy.selectbox("Starting Year", range(today.year, today.year + 2), index=0)
forecast = db.get_monthly_revenue_forecast(forecast_year, 1, 12)

if forecast:
    df_forecast = pd.DataFrame(forecast)
    df_forecast["label"] = df_forecast.apply(
        lambda r: datetime(int(r["year"]), int(r["month"]), 1).strftime("%b %Y"), axis=1
    )

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_forecast["label"],
        y=df_forecast["weighted_revenue"],
        name="Weighted Revenue",
        marker_color="#1f77b4",
    ))
    fig.add_trace(go.Bar(
        x=df_forecast["label"],
        y=df_forecast["weighted_profit"],
        name="Weighted Profit",
        marker_color="#2ca02c",
    ))
    fig.add_trace(go.Scatter(
        x=df_forecast["label"],
        y=df_forecast["director_involvement"],
        name="Director Involvement %",
        yaxis="y2",
        line=dict(color="#d62728", width=2),
        mode="lines+markers",
    ))
    fig.update_layout(
        barmode="group",
        height=400,
        margin=dict(l=20, r=60, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(title="Amount"),
        yaxis2=dict(title="Director %", overlaying="y", side="right", range=[0, 100]),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Forecast table
    with st.expander("Forecast Data Table"):
        display_forecast = df_forecast[["label", "project_count", "weighted_revenue",
                                         "weighted_profit", "director_involvement"]].copy()
        display_forecast.columns = ["Month", "Projects", "Weighted Revenue",
                                     "Weighted Profit", "Director Involvement %"]
        st.dataframe(
            display_forecast.style.format({
                "Weighted Revenue": "{:,.0f}",
                "Weighted Profit": "{:,.0f}",
                "Director Involvement %": "{:.0f}%",
            }),
            use_container_width=True,
            hide_index=True,
        )

    # Annual totals
    annual_revenue = df_forecast["weighted_revenue"].sum()
    annual_profit = df_forecast["weighted_profit"].sum()
    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric(f"Forecast Revenue ({forecast_year})", f"{annual_revenue:,.0f}")
    c2.metric(f"Forecast Profit ({forecast_year})", f"{annual_profit:,.0f}")
    c3.metric("Avg Monthly Revenue", f"{annual_revenue / 12:,.0f}")

# ===================================================================
# DIRECTOR CAPACITY PLANNING
# ===================================================================
st.divider()
st.subheader("Director Capacity Planning")
st.caption("Current allocation from Time Allocation + pipeline estimated involvement.")

directors = db.get_employees(active_only=True)
directors = [d for d in directors if d["role"] == "Director"]

if directors:
    # Current month actual allocation
    actual = db.get_director_capacity(today.year, today.month)
    actual_map = {d["id"]: d["total_allocation"] for d in actual}

    # Pipeline demand (from project director_involvement_pct weighted by likelihood)
    pipeline_director_demand = sum(
        p["director_involvement_pct"] * p["likelihood_pct"] / 100
        for p in pipeline
    )

    cols = st.columns(len(directors))
    for i, d in enumerate(directors):
        with cols[i]:
            current = actual_map.get(d["id"], 0)
            # Estimate future pipeline demand split equally among directors
            pipeline_per_director = pipeline_director_demand / len(directors) if directors else 0
            total_projected = current + pipeline_per_director

            st.markdown(f"**{d['name']}**")
            st.metric("Current Allocation", f"{current:.0f}%")
            st.metric("Pipeline Demand (est.)", f"+{pipeline_per_director:.0f}%")

            # Capacity gauge
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=total_projected,
                title={"text": "Projected Total"},
                gauge={
                    "axis": {"range": [None, 120]},
                    "bar": {"color": "#1f77b4"},
                    "steps": [
                        {"range": [0, 60], "color": "#d4edda"},
                        {"range": [60, 85], "color": "#fff3cd"},
                        {"range": [85, 120], "color": "#f8d7da"},
                    ],
                    "threshold": {
                        "line": {"color": "red", "width": 2},
                        "thickness": 0.75,
                        "value": 100,
                    },
                },
            ))
            fig.update_layout(height=200, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No directors found. Add employees with the 'Director' role.")

# ===================================================================
# EXPORTS ANALYSIS
# ===================================================================
st.divider()
st.subheader("Exports-Oriented Pipeline")

exports_projects = [r for r in rows if r["Exports"] == "Yes"]
domestic_projects = [r for r in rows if r["Exports"] == "No"]

c1, c2 = st.columns(2)
with c1:
    exports_value = sum(r["Weighted Value"] for r in exports_projects)
    st.metric("Exports-Oriented (Weighted)", f"{exports_value:,.0f}")
    st.caption(f"{len(exports_projects)} project(s)")

with c2:
    domestic_value = sum(r["Weighted Value"] for r in domestic_projects)
    st.metric("Domestic (Weighted)", f"{domestic_value:,.0f}")
    st.caption(f"{len(domestic_projects)} project(s)")

if exports_projects or domestic_projects:
    fig = px.pie(
        pd.DataFrame([
            {"Type": "Exports", "Value": exports_value},
            {"Type": "Domestic", "Value": domestic_value},
        ]),
        values="Value", names="Type",
        color_discrete_map={"Exports": "#1f77b4", "Domestic": "#ff7f0e"},
        hole=0.4,
    )
    fig.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)
