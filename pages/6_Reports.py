"""
Reports & Analytics Page
Comprehensive reporting with CSV export capabilities.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import io

import database as db

db.init_db()

st.set_page_config(page_title="Reports - Survey Agency PM", layout="wide")
st.title("Reports & Analytics")

today = date.today()

report_type = st.selectbox("Select Report", [
    "Monthly P&L by Project",
    "Employee Cost Allocation",
    "Employee Utilization",
    "Pipeline Forecast",
    "All Projects Margin Summary",
    "Director Involvement",
])

st.divider()


def to_csv_download(df, filename):
    """Generate CSV download button for a dataframe."""
    csv = df.to_csv(index=False)
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name=filename,
        mime="text/csv",
        use_container_width=True,
    )


# ===================================================================
# MONTHLY P&L BY PROJECT
# ===================================================================
if report_type == "Monthly P&L by Project":
    st.subheader("Monthly P&L by Project")

    col_y, col_m = st.columns([1, 4])
    year = col_y.selectbox("Year", range(today.year - 1, today.year + 2), index=1)
    month_names = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    month = col_m.selectbox("Month", range(1, 13), index=today.month - 1,
                            format_func=lambda x: month_names[x - 1])

    projects = db.get_projects()
    active = [p for p in projects if p["status"] in ("Active", "Pipeline", "On Hold")]

    rows = []
    for proj in active:
        # Monthly personnel cost
        personnel = db.get_project_personnel_costs(proj["id"], year, month)
        monthly_personnel = sum(p["cost"] for p in personnel)

        # Non-personnel (total - not monthly, but we show it for context)
        non_personnel = db.get_budget_total(proj["id"])

        # Monthly revenue = contract / duration
        duration = proj["expected_duration_months"] or 1
        monthly_revenue = proj["contract_value"] / duration

        monthly_total_cost = monthly_personnel  # Monthly only has personnel as variable
        monthly_margin = monthly_revenue - monthly_total_cost

        rows.append({
            "Project": proj["name"],
            "Client": proj["client"],
            "Status": proj["status"],
            "Monthly Revenue": monthly_revenue,
            "Personnel Cost": monthly_personnel,
            "Monthly Margin": monthly_margin,
            "Margin %": (monthly_margin / monthly_revenue * 100) if monthly_revenue > 0 else 0,
            "Employees": len(personnel),
        })

    if rows:
        df_pnl = pd.DataFrame(rows)

        st.dataframe(
            df_pnl.style.format({
                "Monthly Revenue": "{:,.0f}",
                "Personnel Cost": "{:,.0f}",
                "Monthly Margin": "{:,.0f}",
                "Margin %": "{:.1f}%",
            }),
            use_container_width=True,
            hide_index=True,
        )

        # Totals
        total_rev = df_pnl["Monthly Revenue"].sum()
        total_cost = df_pnl["Personnel Cost"].sum()
        total_margin = df_pnl["Monthly Margin"].sum()

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Monthly Revenue", f"{total_rev:,.0f}")
        c2.metric("Total Personnel Cost", f"{total_cost:,.0f}")
        c3.metric("Total Monthly Margin", f"{total_margin:,.0f}")

        # Chart
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_pnl["Project"], y=df_pnl["Monthly Revenue"], name="Revenue"))
        fig.add_trace(go.Bar(x=df_pnl["Project"], y=df_pnl["Personnel Cost"], name="Cost"))
        fig.update_layout(barmode="group", height=350,
                          margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig, use_container_width=True)

        to_csv_download(df_pnl, f"pnl_{year}_{month:02d}.csv")
    else:
        st.info("No active projects for this period.")


# ===================================================================
# EMPLOYEE COST ALLOCATION
# ===================================================================
elif report_type == "Employee Cost Allocation":
    st.subheader("Employee Cost Allocation Report")

    col_y, col_m = st.columns([1, 4])
    year = col_y.selectbox("Year", range(today.year - 1, today.year + 2), index=1)
    month_names = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    month = col_m.selectbox("Month", range(1, 13), index=today.month - 1,
                            format_func=lambda x: month_names[x - 1])

    allocations = db.get_allocations_for_month(year, month)

    if allocations:
        rows = []
        for a in allocations:
            cost = a["monthly_salary"] * a["allocation_pct"] / 100.0
            rows.append({
                "Employee": a["employee_name"],
                "Role": a["employee_role"],
                "Monthly Salary": a["monthly_salary"],
                "Project": a["project_name"],
                "Allocation %": a["allocation_pct"],
                "Cost to Project": cost,
            })

        df_alloc = pd.DataFrame(rows)

        # Pivot table: employees × projects
        st.markdown("**Cost Allocation Matrix**")
        pivot = df_alloc.pivot_table(
            index=["Employee", "Role"],
            columns="Project",
            values="Cost to Project",
            aggfunc="sum",
            fill_value=0,
        )
        pivot["TOTAL"] = pivot.sum(axis=1)

        st.dataframe(
            pivot.style.format("{:,.0f}"),
            use_container_width=True,
        )

        st.divider()

        # By project summary
        st.markdown("**Cost by Project**")
        by_project = df_alloc.groupby("Project")["Cost to Project"].sum().reset_index()
        by_project.columns = ["Project", "Total Cost"]
        by_project = by_project.sort_values("Total Cost", ascending=False)

        col_t, col_c = st.columns(2)
        with col_t:
            st.dataframe(
                by_project.style.format({"Total Cost": "{:,.0f}"}),
                use_container_width=True,
                hide_index=True,
            )
        with col_c:
            fig = px.pie(by_project, values="Total Cost", names="Project",
                         color_discrete_sequence=px.colors.qualitative.Set2, hole=0.3)
            fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)

        to_csv_download(df_alloc, f"cost_allocation_{year}_{month:02d}.csv")
    else:
        st.info("No allocations for this period.")


# ===================================================================
# EMPLOYEE UTILIZATION
# ===================================================================
elif report_type == "Employee Utilization":
    st.subheader("Employee Utilization Report")

    col_y, col_m = st.columns([1, 4])
    year = col_y.selectbox("Year", range(today.year - 1, today.year + 2), index=1)
    month_names = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    month = col_m.selectbox("Month", range(1, 13), index=today.month - 1,
                            format_func=lambda x: month_names[x - 1])

    utilization = db.get_employee_utilization(year, month)

    if utilization:
        df_util = pd.DataFrame(utilization)
        df_util["status"] = df_util["total_allocation"].apply(
            lambda x: "Over-allocated" if x > 100
            else "Well-utilized" if x >= 80
            else "Moderate" if x >= 50
            else "Under-utilized" if x > 0
            else "Unallocated"
        )
        df_util["unallocated"] = (100 - df_util["total_allocation"]).clip(lower=0)
        df_util["wasted_salary"] = df_util["monthly_salary"] * df_util["unallocated"] / 100.0

        display = df_util[["name", "role", "monthly_salary", "total_allocation", "status", "wasted_salary"]].copy()
        display.columns = ["Employee", "Role", "Monthly Salary", "Utilization %", "Status", "Unallocated Cost"]

        st.dataframe(
            display.style.format({
                "Monthly Salary": "{:,.0f}",
                "Utilization %": "{:.0f}%",
                "Unallocated Cost": "{:,.0f}",
            }),
            use_container_width=True,
            hide_index=True,
        )

        # Summary
        avg_util = df_util["total_allocation"].mean()
        total_wasted = df_util["wasted_salary"].sum()
        over_count = len(df_util[df_util["total_allocation"] > 100])

        c1, c2, c3 = st.columns(3)
        c1.metric("Average Utilization", f"{avg_util:.0f}%")
        c2.metric("Unallocated Salary Cost", f"{total_wasted:,.0f}")
        c3.metric("Over-allocated Staff", over_count)

        # Chart
        fig = go.Figure()
        df_sorted = df_util.sort_values("total_allocation", ascending=True)
        colors = []
        for val in df_sorted["total_allocation"]:
            if val > 100:
                colors.append("#d62728")
            elif val >= 80:
                colors.append("#2ca02c")
            elif val >= 50:
                colors.append("#ff7f0e")
            else:
                colors.append("#aec7e8")

        fig.add_trace(go.Bar(
            x=df_sorted["total_allocation"],
            y=df_sorted["name"],
            orientation="h",
            marker_color=colors,
            text=df_sorted["total_allocation"].apply(lambda x: f"{x:.0f}%"),
            textposition="auto",
        ))
        fig.add_vline(x=100, line_dash="dash", line_color="red", opacity=0.5)
        fig.update_layout(height=max(350, len(df_sorted) * 35),
                          margin=dict(l=20, r=20, t=10, b=20),
                          xaxis_title="Utilization %")
        st.plotly_chart(fig, use_container_width=True)

        # By role
        st.divider()
        st.markdown("**Utilization by Role**")
        role_util = df_util.groupby("role").agg(
            employees=("name", "count"),
            avg_util=("total_allocation", "mean"),
            total_salary=("monthly_salary", "sum"),
            total_wasted=("wasted_salary", "sum"),
        ).reset_index()
        role_util.columns = ["Role", "Employees", "Avg Utilization %", "Total Salary", "Unallocated Cost"]
        st.dataframe(
            role_util.style.format({
                "Avg Utilization %": "{:.0f}%",
                "Total Salary": "{:,.0f}",
                "Unallocated Cost": "{:,.0f}",
            }),
            use_container_width=True,
            hide_index=True,
        )

        to_csv_download(display, f"utilization_{year}_{month:02d}.csv")
    else:
        st.info("No employees found.")


# ===================================================================
# PIPELINE FORECAST
# ===================================================================
elif report_type == "Pipeline Forecast":
    st.subheader("Pipeline Revenue Forecast")

    forecast_year = st.selectbox("Year", range(today.year, today.year + 2), index=0)
    forecast = db.get_monthly_revenue_forecast(forecast_year, 1, 12)

    if forecast:
        df_fc = pd.DataFrame(forecast)
        df_fc["label"] = df_fc.apply(
            lambda r: datetime(int(r["year"]), int(r["month"]), 1).strftime("%b %Y"), axis=1
        )

        display_fc = df_fc[["label", "project_count", "revenue", "weighted_revenue",
                            "profit", "weighted_profit", "director_involvement"]].copy()
        display_fc.columns = ["Month", "Projects", "Gross Revenue", "Weighted Revenue",
                              "Gross Profit", "Weighted Profit", "Director Inv. %"]

        st.dataframe(
            display_fc.style.format({
                "Gross Revenue": "{:,.0f}",
                "Weighted Revenue": "{:,.0f}",
                "Gross Profit": "{:,.0f}",
                "Weighted Profit": "{:,.0f}",
                "Director Inv. %": "{:.0f}%",
            }),
            use_container_width=True,
            hide_index=True,
        )

        # Annual summaries
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Annual Gross Revenue", f"{df_fc['revenue'].sum():,.0f}")
        c2.metric("Annual Weighted Revenue", f"{df_fc['weighted_revenue'].sum():,.0f}")
        c3.metric("Annual Weighted Profit", f"{df_fc['weighted_profit'].sum():,.0f}")
        c4.metric("Avg Director Load", f"{df_fc['director_involvement'].mean():.0f}%")

        # Cumulative chart
        fig = go.Figure()
        df_fc["cum_revenue"] = df_fc["weighted_revenue"].cumsum()
        df_fc["cum_profit"] = df_fc["weighted_profit"].cumsum()

        fig.add_trace(go.Scatter(
            x=df_fc["label"], y=df_fc["cum_revenue"],
            name="Cumulative Revenue", fill="tozeroy",
            line=dict(color="#1f77b4"),
        ))
        fig.add_trace(go.Scatter(
            x=df_fc["label"], y=df_fc["cum_profit"],
            name="Cumulative Profit", fill="tozeroy",
            line=dict(color="#2ca02c"),
        ))
        fig.update_layout(height=350, margin=dict(l=20, r=20, t=30, b=20),
                          yaxis_title="Cumulative Amount")
        st.plotly_chart(fig, use_container_width=True)

        to_csv_download(display_fc, f"pipeline_forecast_{forecast_year}.csv")
    else:
        st.info("No forecast data available.")


# ===================================================================
# ALL PROJECTS MARGIN SUMMARY
# ===================================================================
elif report_type == "All Projects Margin Summary":
    st.subheader("All Projects - Margin Summary")

    margins = db.get_all_project_margins()

    if margins:
        df_margins = pd.DataFrame(margins)
        display_m = df_margins[[
            "project_name", "client", "status", "revenue",
            "personnel_cost", "non_personnel_cost", "total_cost",
            "margin", "margin_pct"
        ]].copy()
        display_m.columns = [
            "Project", "Client", "Status", "Revenue",
            "Personnel Cost", "Non-Personnel Cost", "Total Cost",
            "Margin", "Margin %"
        ]

        st.dataframe(
            display_m.style.format({
                "Revenue": "{:,.0f}",
                "Personnel Cost": "{:,.0f}",
                "Non-Personnel Cost": "{:,.0f}",
                "Total Cost": "{:,.0f}",
                "Margin": "{:,.0f}",
                "Margin %": "{:.1f}%",
            }),
            use_container_width=True,
            hide_index=True,
        )

        # Summary
        total_rev = display_m["Revenue"].sum()
        total_cost = display_m["Total Cost"].sum()
        total_margin = display_m["Margin"].sum()
        overall_pct = (total_margin / total_rev * 100) if total_rev > 0 else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Revenue", f"{total_rev:,.0f}")
        c2.metric("Total Cost", f"{total_cost:,.0f}")
        c3.metric("Total Margin", f"{total_margin:,.0f}")
        c4.metric("Overall Margin %", f"{overall_pct:.1f}%")

        # Margin distribution
        fig = px.histogram(display_m, x="Margin %", nbins=10,
                          color_discrete_sequence=["#1f77b4"])
        fig.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig, use_container_width=True)

        to_csv_download(display_m, "project_margins.csv")
    else:
        st.info("No projects with margin data.")


# ===================================================================
# DIRECTOR INVOLVEMENT
# ===================================================================
elif report_type == "Director Involvement":
    st.subheader("Director Involvement Report")

    year = st.selectbox("Year", range(today.year - 1, today.year + 2), index=1)

    directors = db.get_employees(active_only=True)
    directors = [d for d in directors if d["role"] == "Director"]

    if not directors:
        st.info("No directors found.")
        st.stop()

    month_names = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ]

    # Build monthly data for each director
    all_data = []
    for d in directors:
        for m in range(1, 13):
            total = db.get_employee_total_allocation(d["id"], year, m)
            all_data.append({
                "Director": d["name"],
                "Month": month_names[m - 1],
                "Month_Num": m,
                "Allocation %": total,
                "Salary Cost": d["monthly_salary"] * total / 100.0,
            })

    df_directors = pd.DataFrame(all_data)

    # Pivot table
    pivot = df_directors.pivot_table(
        index="Director",
        columns="Month",
        values="Allocation %",
        aggfunc="sum",
    )
    # Reorder columns by month
    ordered_months = [m for m in month_names if m in pivot.columns]
    pivot = pivot[ordered_months]

    st.markdown("**Monthly Allocation % by Director**")
    st.dataframe(
        pivot.style.format("{:.0f}%").background_gradient(cmap="YlOrRd", vmin=0, vmax=100),
        use_container_width=True,
    )

    # Chart
    fig = go.Figure()
    for d in directors:
        d_data = df_directors[df_directors["Director"] == d["name"]].sort_values("Month_Num")
        fig.add_trace(go.Scatter(
            x=d_data["Month"],
            y=d_data["Allocation %"],
            name=d["name"],
            mode="lines+markers",
        ))
    fig.add_hline(y=100, line_dash="dash", line_color="red", opacity=0.5)
    fig.update_layout(
        height=350,
        margin=dict(l=20, r=20, t=30, b=20),
        yaxis_title="Allocation %",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Cost summary
    st.divider()
    st.markdown("**Director Cost Allocation**")
    cost_pivot = df_directors.pivot_table(
        index="Director",
        columns="Month",
        values="Salary Cost",
        aggfunc="sum",
    )
    cost_pivot = cost_pivot[[m for m in month_names if m in cost_pivot.columns]]
    cost_pivot["Annual Total"] = cost_pivot.sum(axis=1)

    st.dataframe(
        cost_pivot.style.format("{:,.0f}"),
        use_container_width=True,
    )

    to_csv_download(df_directors, f"director_involvement_{year}.csv")
