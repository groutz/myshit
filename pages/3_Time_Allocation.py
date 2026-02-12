"""
Time Allocation Page
Monthly employee-to-project percentage assignment grid.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date

import database as db

db.init_db()

st.set_page_config(page_title="Time Allocation - Survey Agency PM", layout="wide")
st.title("Monthly Time Allocation")
st.caption("Assign employee time (%) to projects for each month. Salary costs are calculated automatically.")

# --- Month Selector ---
today = date.today()
col_y, col_m, _ = st.columns([1, 1, 3])
year = col_y.selectbox("Year", range(today.year - 1, today.year + 3), index=1)
month_names = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]
month = col_m.selectbox("Month", range(1, 13), index=today.month - 1,
                        format_func=lambda x: month_names[x - 1])

st.divider()

# --- Get Data ---
employees = db.get_employees(active_only=True)
projects = db.get_projects()
# Only show active and pipeline projects for allocation
eligible_projects = [p for p in projects if p["status"] in ("Active", "Pipeline", "On Hold")]

if not employees:
    st.warning("No active employees. Add employees first.")
    st.stop()
if not eligible_projects:
    st.warning("No active/pipeline projects. Add projects first.")
    st.stop()

# Build current allocations map
allocations = db.get_allocations_for_month(year, month)
alloc_map = {}
for a in allocations:
    alloc_map[(a["employee_id"], a["project_id"])] = a["allocation_pct"]

# --- Build Editable Grid ---
st.subheader(f"Allocation Grid - {month_names[month - 1]} {year}")
st.caption("Enter the percentage of each employee's time allocated to each project. Row totals should not exceed 100%.")

# Create dataframe for the grid
proj_names = [p["name"] for p in eligible_projects]
proj_ids = [p["id"] for p in eligible_projects]

grid_data = []
for emp in employees:
    row = {"Employee": emp["name"], "Role": emp["role"], "Salary": emp["monthly_salary"]}
    total = 0
    for proj in eligible_projects:
        val = alloc_map.get((emp["id"], proj["id"]), 0.0)
        row[proj["name"]] = val
        total += val
    row["TOTAL %"] = total
    grid_data.append(row)

df_grid = pd.DataFrame(grid_data)

# Use data_editor for interactive editing
column_config = {
    "Employee": st.column_config.TextColumn("Employee", disabled=True, width="medium"),
    "Role": st.column_config.TextColumn("Role", disabled=True, width="small"),
    "Salary": st.column_config.NumberColumn("Salary", disabled=True, format="%.0f", width="small"),
    "TOTAL %": st.column_config.NumberColumn("TOTAL %", disabled=True, format="%.0f", width="small"),
}

for pname in proj_names:
    column_config[pname] = st.column_config.NumberColumn(
        pname,
        min_value=0.0,
        max_value=100.0,
        step=5.0,
        format="%.0f",
        width="small",
    )

edited_df = st.data_editor(
    df_grid,
    column_config=column_config,
    use_container_width=True,
    hide_index=True,
    num_rows="fixed",
    key="allocation_grid",
)

# --- Validation & Save ---
# Recalculate totals from edited data
warnings = []
for idx, row in edited_df.iterrows():
    total = sum(row[pname] for pname in proj_names)
    if total > 100:
        warnings.append(f"{row['Employee']}: {total:.0f}% (exceeds 100%)")

if warnings:
    st.warning("Over-allocation detected:\n" + "\n".join(f"- {w}" for w in warnings))

if st.button("Save Allocations", type="primary", use_container_width=True):
    saved = 0
    for idx, row in edited_df.iterrows():
        emp = employees[idx]
        for i, proj in enumerate(eligible_projects):
            new_val = float(row[proj["name"]])
            old_val = alloc_map.get((emp["id"], proj["id"]), 0.0)
            if new_val != old_val:
                db.set_allocation(emp["id"], proj["id"], year, month, new_val)
                saved += 1

    if saved > 0:
        st.success(f"Saved {saved} allocation changes.")
        st.rerun()
    else:
        st.info("No changes to save.")

# --- Cost Summary ---
st.divider()
st.subheader("Salary Cost Allocation")
st.caption("How much of each employee's salary is charged to each project this month.")

cost_rows = []
for idx, row in edited_df.iterrows():
    emp = employees[idx]
    salary = emp["monthly_salary"]
    for proj in eligible_projects:
        pct = float(row[proj["name"]])
        if pct > 0:
            cost = salary * pct / 100.0
            cost_rows.append({
                "Employee": emp["name"],
                "Role": emp["role"],
                "Project": proj["name"],
                "Allocation %": pct,
                "Monthly Salary": salary,
                "Cost to Project": cost,
            })

if cost_rows:
    df_costs = pd.DataFrame(cost_rows)

    # Summary by project
    st.markdown("**Cost by Project**")
    project_costs = df_costs.groupby("Project").agg(
        Employees=("Employee", "count"),
        Total_Cost=("Cost to Project", "sum")
    ).reset_index()
    project_costs.columns = ["Project", "Employees Assigned", "Total Personnel Cost"]
    st.dataframe(
        project_costs.style.format({"Total Personnel Cost": "{:,.0f}"}),
        use_container_width=True,
        hide_index=True,
    )

    # Detailed breakdown
    with st.expander("Detailed Cost Breakdown"):
        st.dataframe(
            df_costs.style.format({
                "Allocation %": "{:.0f}%",
                "Monthly Salary": "{:,.0f}",
                "Cost to Project": "{:,.0f}",
            }),
            use_container_width=True,
            hide_index=True,
        )

    # Total salary cost this month
    total_allocated_cost = df_costs["Cost to Project"].sum()
    total_salary = sum(e["monthly_salary"] for e in employees)
    unallocated = total_salary - total_allocated_cost

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Payroll", f"{total_salary:,.0f}")
    m2.metric("Allocated to Projects", f"{total_allocated_cost:,.0f}")
    m3.metric("Unallocated", f"{unallocated:,.0f}")
else:
    st.info("No allocations set for this month. Enter percentages in the grid above.")
