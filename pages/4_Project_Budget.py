"""
Project Budget Page
Full cost breakdown and margin calculation per project.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date

import database as db

db.init_db()

st.set_page_config(page_title="Project Budget - Survey Agency PM", layout="wide")
st.title("Project Budget & Margin")
st.caption("View and manage project costs to calculate expected margins.")

# --- Project Selector ---
projects = db.get_projects()
active_and_pipeline = [p for p in projects if p["status"] in ("Active", "Pipeline", "On Hold")]

if not active_and_pipeline:
    st.info("No active or pipeline projects. Create a project first.")
    st.stop()

project_options = {f"{p['name']} [{p['status']}] - {p['client']}": p["id"] for p in active_and_pipeline}
selected = st.selectbox("Select Project", list(project_options.keys()))
project_id = project_options[selected]
project = db.get_project(project_id)

st.divider()

# --- Project Info Header ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Contract Value", f"{project['contract_value']:,.0f}")
col2.metric("Status", project["status"])
col3.metric("Method", project["implementation_method"])
col4.metric("Duration", f"{project['expected_duration_months']} months")

st.divider()

# ===================================================================
# PERSONNEL COSTS (auto-calculated from Time Allocation)
# ===================================================================
st.subheader("Personnel Costs")
st.caption("Automatically calculated from the Time Allocation page. Edit allocations there to adjust these costs.")

personnel = db.get_project_personnel_costs(project_id)

if personnel:
    df_personnel = pd.DataFrame(personnel)
    # Aggregate by employee across all months
    agg = df_personnel.groupby(["employee_name", "employee_role", "monthly_salary"]).agg(
        months=("month", "count"),
        avg_allocation=("allocation_pct", "mean"),
        total_cost=("cost", "sum"),
    ).reset_index()
    agg.columns = ["Employee", "Role", "Monthly Salary", "Months Active", "Avg Allocation %", "Total Cost"]

    st.dataframe(
        agg.style.format({
            "Monthly Salary": "{:,.0f}",
            "Avg Allocation %": "{:.0f}%",
            "Total Cost": "{:,.0f}",
        }),
        use_container_width=True,
        hide_index=True,
    )

    total_personnel = agg["Total Cost"].sum()
    st.metric("Total Personnel Cost", f"{total_personnel:,.0f}")

    # Monthly breakdown
    with st.expander("Monthly Personnel Cost Breakdown"):
        monthly = df_personnel.groupby(["year", "month"]).agg(
            employees=("employee_name", "nunique"),
            cost=("cost", "sum"),
        ).reset_index()
        monthly["period"] = monthly.apply(
            lambda r: datetime(int(r["year"]), int(r["month"]), 1).strftime("%b %Y"), axis=1
        )
        monthly.columns = ["Year", "Month", "Employees", "Cost", "Period"]
        st.dataframe(
            monthly[["Period", "Employees", "Cost"]].style.format({"Cost": "{:,.0f}"}),
            use_container_width=True,
            hide_index=True,
        )
else:
    total_personnel = 0
    st.info("No personnel allocated to this project. Use the Time Allocation page to assign employees.")

st.divider()

# ===================================================================
# NON-PERSONNEL COSTS (Equipment, Tools, Suppliers, etc.)
# ===================================================================
st.subheader("Non-Personnel Costs")

budget_items = db.get_budget_items(project_id)

if budget_items:
    df_budget = pd.DataFrame(budget_items)
    st.dataframe(
        df_budget[["category", "description", "amount", "notes"]].rename(columns={
            "category": "Category",
            "description": "Description",
            "amount": "Amount",
            "notes": "Notes",
        }).style.format({"Amount": "{:,.0f}"}),
        use_container_width=True,
        hide_index=True,
    )

    # Summary by category
    cat_summary = df_budget.groupby("category")["amount"].sum().reset_index()
    cat_summary.columns = ["Category", "Total"]

    col_table, col_chart = st.columns([1, 1])
    with col_table:
        st.dataframe(
            cat_summary.style.format({"Total": "{:,.0f}"}),
            use_container_width=True,
            hide_index=True,
        )
    with col_chart:
        fig = px.pie(cat_summary, values="Total", names="Category",
                     color_discrete_sequence=px.colors.qualitative.Set2,
                     hole=0.3)
        fig.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

total_non_personnel = db.get_budget_total(project_id)

# Add budget item
st.markdown("**Add Cost Item**")
with st.form("add_budget_item"):
    cols = st.columns([1, 2, 1, 2])
    new_cat = cols[0].selectbox("Category", db.BUDGET_CATEGORIES)
    new_desc = cols[1].text_input("Description")
    new_amount = cols[2].number_input("Amount", min_value=0.0, step=100.0, format="%.0f")
    new_notes = cols[3].text_input("Notes")

    if st.form_submit_button("Add Item", use_container_width=True):
        if not new_desc.strip():
            st.error("Description is required.")
        elif new_amount <= 0:
            st.error("Amount must be greater than 0.")
        else:
            db.add_budget_item(project_id, new_cat, new_desc.strip(), new_amount, new_notes.strip())
            st.success("Budget item added.")
            st.rerun()

# Delete budget item
if budget_items:
    with st.expander("Remove a Cost Item"):
        item_options = {f"{b['category']}: {b['description']} ({b['amount']:,.0f})": b["id"]
                       for b in budget_items}
        item_to_delete = st.selectbox("Select item to remove", [""] + list(item_options.keys()))
        if item_to_delete and item_to_delete in item_options:
            if st.button("Delete Selected Item", type="secondary"):
                db.delete_budget_item(item_options[item_to_delete])
                st.success("Item removed.")
                st.rerun()

st.divider()

# ===================================================================
# MARGIN CALCULATION
# ===================================================================
st.subheader("Project Margin Summary")

revenue = project["contract_value"] or 0
total_cost = total_personnel + total_non_personnel
margin = revenue - total_cost
margin_pct = (margin / revenue * 100) if revenue > 0 else 0

col_a, col_b, col_c = st.columns(3)

with col_a:
    st.markdown("**Revenue**")
    st.markdown(f"### {revenue:,.0f}")

with col_b:
    st.markdown("**Total Costs**")
    st.markdown(f"### {total_cost:,.0f}")
    st.caption(f"Personnel: {total_personnel:,.0f} | Other: {total_non_personnel:,.0f}")

with col_c:
    color = "green" if margin >= 0 else "red"
    st.markdown("**Margin**")
    st.markdown(f"### :{color}[{margin:,.0f} ({margin_pct:.1f}%)]")

# Visual waterfall
fig = go.Figure(go.Waterfall(
    name="Budget",
    orientation="v",
    measure=["absolute", "relative", "relative", "total"],
    x=["Revenue", "Personnel Costs", "Non-Personnel Costs", "Margin"],
    y=[revenue, -total_personnel, -total_non_personnel, 0],
    text=[f"{revenue:,.0f}", f"-{total_personnel:,.0f}", f"-{total_non_personnel:,.0f}", f"{margin:,.0f}"],
    textposition="outside",
    connector={"line": {"color": "rgb(63, 63, 63)"}},
    increasing={"marker": {"color": "#2ca02c"}},
    decreasing={"marker": {"color": "#d62728"}},
    totals={"marker": {"color": "#1f77b4"}},
))
fig.update_layout(
    height=350,
    margin=dict(l=20, r=20, t=30, b=20),
    showlegend=False,
)
st.plotly_chart(fig, use_container_width=True)

# --- Comparison with Expected Margin ---
if project["expected_margin_pct"]:
    expected_margin_pct = project["expected_margin_pct"]
    expected_margin_amount = revenue * expected_margin_pct / 100
    variance = margin - expected_margin_amount
    st.divider()
    st.subheader("Expected vs. Actual Margin")
    c1, c2, c3 = st.columns(3)
    c1.metric("Expected Margin", f"{expected_margin_amount:,.0f} ({expected_margin_pct:.0f}%)")
    c2.metric("Calculated Margin", f"{margin:,.0f} ({margin_pct:.1f}%)")
    c3.metric("Variance", f"{variance:,.0f}", delta=f"{margin_pct - expected_margin_pct:.1f}pp")
