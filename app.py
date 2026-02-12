"""
Survey Agency - Project & HR Management Tool
Main Dashboard
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date

import database as db

# Initialize database
db.init_db()

st.set_page_config(
    page_title="Survey Agency PM",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sidebar
st.sidebar.title("Survey Agency PM")
st.sidebar.caption("Project & HR Management")
st.sidebar.divider()

if st.sidebar.button("Load Demo Data", use_container_width=True):
    db.seed_demo_data()
    st.rerun()

st.sidebar.divider()
st.sidebar.markdown(
    """
    **Navigation**
    - **Dashboard** (this page)
    - **Employees** - Manage staff
    - **Projects** - Manage projects
    - **Time Allocation** - Monthly assignments
    - **Project Budget** - Costs & margins
    - **Pipeline** - Forecasting
    - **Reports** - Analytics & exports
    """
)

# Main content
st.title("Dashboard")

today = date.today()
current_year = today.year
current_month = today.month

# Fetch data
employees = db.get_employees(active_only=True)
all_projects = db.get_projects()
active_projects = [p for p in all_projects if p["status"] == "Active"]
pipeline_projects = [p for p in all_projects if p["status"] == "Pipeline"]
utilization = db.get_employee_utilization(current_year, current_month)
forecast = db.get_monthly_revenue_forecast(current_year, current_month, 12)

# --- KPI Row ---
st.subheader("Key Metrics")
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.metric("Active Employees", len(employees))

with kpi2:
    st.metric("Active Projects", len(active_projects))

with kpi3:
    pipeline_value = sum(p["contract_value"] for p in pipeline_projects)
    weighted_pipeline = sum(
        p["contract_value"] * p["likelihood_pct"] / 100 for p in pipeline_projects
    )
    st.metric(
        "Pipeline (Weighted)",
        f"{weighted_pipeline:,.0f}",
        delta=f"{pipeline_value:,.0f} total",
    )

with kpi4:
    avg_util = 0
    if utilization:
        avg_util = sum(u["total_allocation"] for u in utilization) / len(utilization)
    st.metric(
        f"Avg Utilization ({datetime(current_year, current_month, 1).strftime('%b %Y')})",
        f"{avg_util:.0f}%",
    )

st.divider()

# --- Revenue Forecast ---
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Revenue Forecast (12 Months)")
    if forecast:
        df_forecast = pd.DataFrame(forecast)
        df_forecast["month_label"] = df_forecast.apply(
            lambda r: datetime(int(r["year"]), int(r["month"]), 1).strftime("%b %Y"),
            axis=1,
        )
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_forecast["month_label"],
            y=df_forecast["weighted_revenue"],
            name="Weighted Revenue",
            marker_color="#1f77b4",
        ))
        fig.add_trace(go.Bar(
            x=df_forecast["month_label"],
            y=df_forecast["weighted_profit"],
            name="Weighted Profit",
            marker_color="#2ca02c",
        ))
        fig.update_layout(
            barmode="overlay",
            height=350,
            margin=dict(l=20, r=20, t=30, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No forecast data available. Add projects with dates to see forecasts.")

with col_right:
    st.subheader(f"Employee Utilization - {datetime(current_year, current_month, 1).strftime('%B %Y')}")
    if utilization:
        df_util = pd.DataFrame(utilization)
        df_util = df_util.sort_values("total_allocation", ascending=True)

        colors = []
        for val in df_util["total_allocation"]:
            if val > 100:
                colors.append("#d62728")  # Over-allocated
            elif val >= 80:
                colors.append("#2ca02c")  # Well utilized
            elif val >= 50:
                colors.append("#ff7f0e")  # Moderate
            else:
                colors.append("#aec7e8")  # Under-utilized

        fig = go.Figure(go.Bar(
            x=df_util["total_allocation"],
            y=df_util["name"],
            orientation="h",
            marker_color=colors,
            text=df_util["total_allocation"].apply(lambda x: f"{x:.0f}%"),
            textposition="auto",
        ))
        fig.add_vline(x=100, line_dash="dash", line_color="red", opacity=0.5)
        fig.update_layout(
            height=max(350, len(df_util) * 30),
            margin=dict(l=20, r=20, t=10, b=20),
            xaxis_title="Allocation %",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No allocation data for this month.")

st.divider()

# --- Project Overview ---
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Projects by Status")
    if all_projects:
        status_counts = {}
        for p in all_projects:
            status_counts[p["status"]] = status_counts.get(p["status"], 0) + 1
        df_status = pd.DataFrame(
            [{"Status": k, "Count": v} for k, v in status_counts.items()]
        )
        fig = px.pie(
            df_status, values="Count", names="Status",
            color_discrete_sequence=px.colors.qualitative.Set2,
            hole=0.4,
        )
        fig.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No projects yet.")

with col_b:
    st.subheader("Project Margins")
    margins = db.get_all_project_margins()
    if margins:
        df_margins = pd.DataFrame(margins)
        df_margins = df_margins[df_margins["status"].isin(["Active", "Pipeline"])]
        if not df_margins.empty:
            df_margins = df_margins.sort_values("margin_pct", ascending=True)
            colors = ["#d62728" if x < 0 else "#2ca02c" for x in df_margins["margin_pct"]]
            fig = go.Figure(go.Bar(
                x=df_margins["margin_pct"],
                y=df_margins["project_name"],
                orientation="h",
                marker_color=colors,
                text=df_margins["margin_pct"].apply(lambda x: f"{x:.1f}%"),
                textposition="auto",
            ))
            fig.update_layout(
                height=max(300, len(df_margins) * 35),
                margin=dict(l=20, r=20, t=10, b=20),
                xaxis_title="Margin %",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No active/pipeline projects with margin data.")
    else:
        st.info("No margin data available.")

st.divider()

# --- Director Capacity ---
st.subheader(f"Director Capacity - {datetime(current_year, current_month, 1).strftime('%B %Y')}")
directors = db.get_director_capacity(current_year, current_month)
if directors:
    cols = st.columns(len(directors))
    for i, d in enumerate(directors):
        with cols[i]:
            allocated = d["total_allocation"]
            available = max(0, 100 - allocated)
            st.metric(d["name"], f"{allocated:.0f}% allocated", delta=f"{available:.0f}% available")
else:
    st.info("No directors found. Add employees with the Director role.")

# --- Active Projects Table ---
st.divider()
st.subheader("Active Projects")
if active_projects:
    df_active = pd.DataFrame(active_projects)[
        ["name", "client", "implementation_method", "contract_value", "start_date", "end_date"]
    ]
    df_active.columns = ["Project", "Client", "Method", "Contract Value", "Start", "End"]
    st.dataframe(
        df_active.style.format({"Contract Value": "{:,.0f}"}),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No active projects. Go to Projects to add some.")
