"""
Employee Management Page
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date

import database as db
from theme import apply_theme

db.init_db()

st.set_page_config(page_title="Employees - Survey Agency PM", layout="wide")
apply_theme()
st.title("Employee Management")

# --- State ---
if "edit_employee_id" not in st.session_state:
    st.session_state.edit_employee_id = None

# --- Add Employee Form ---
with st.expander("Add New Employee", expanded=False):
    with st.form("add_employee_form"):
        cols = st.columns([2, 1, 1])
        name = cols[0].text_input("Full Name*")
        role = cols[1].selectbox("Role*", db.ROLES)
        salary = cols[2].number_input("Monthly Salary*", min_value=0.0, step=100.0, format="%.0f")

        cols2 = st.columns([1, 1, 1, 2])
        email = cols2[0].text_input("Email")
        phone = cols2[1].text_input("Phone")
        hire_date = cols2[2].date_input("Hire Date", value=date.today())
        notes = cols2[3].text_input("Notes")

        submitted = st.form_submit_button("Add Employee", use_container_width=True)
        if submitted:
            if not name.strip():
                st.error("Name is required.")
            elif salary <= 0:
                st.error("Salary must be greater than 0.")
            else:
                db.add_employee(
                    name.strip(), role, salary, email.strip(),
                    phone.strip(), hire_date.strftime("%Y-%m-%d"), notes.strip()
                )
                st.success(f"Added {name}.")
                st.rerun()

st.divider()

# --- Filters ---
col_f1, col_f2 = st.columns([1, 3])
show_active_only = col_f1.checkbox("Active only", value=True)
role_filter = col_f2.multiselect("Filter by role", db.ROLES, default=[])

# --- Employee List ---
employees = db.get_employees(active_only=show_active_only)
if role_filter:
    employees = [e for e in employees if e["role"] in role_filter]

if not employees:
    st.info("No employees found. Add one above.")
    st.stop()

# Current month utilization
today = date.today()
utilization_data = db.get_employee_utilization(today.year, today.month)
util_map = {u["id"]: u["total_allocation"] for u in utilization_data}

# Build display dataframe
rows = []
for e in employees:
    util = util_map.get(e["id"], 0)
    rows.append({
        "ID": e["id"],
        "Name": e["name"],
        "Role": e["role"],
        "Monthly Salary": e["monthly_salary"],
        "Email": e["email"],
        "Hire Date": e["hire_date"],
        "Active": "Yes" if e["is_active"] else "No",
        "Utilization": f"{util:.0f}%",
    })

df = pd.DataFrame(rows)

st.subheader(f"Employees ({len(employees)})")
st.dataframe(
    df.style.format({"Monthly Salary": "{:,.0f}"}),
    use_container_width=True,
    hide_index=True,
)

# --- Summary by Role ---
st.divider()
st.subheader("Summary by Role")
role_summary = {}
for e in employees:
    r = e["role"]
    if r not in role_summary:
        role_summary[r] = {"count": 0, "total_salary": 0}
    role_summary[r]["count"] += 1
    role_summary[r]["total_salary"] += e["monthly_salary"]

cols = st.columns(len(role_summary))
for i, (role_name, data) in enumerate(role_summary.items()):
    with cols[i]:
        st.metric(role_name, f"{data['count']} staff")
        st.caption(f"Total monthly: {data['total_salary']:,.0f}")

# --- Edit / Delete ---
st.divider()
st.subheader("Edit or Remove Employee")

employee_options = {f"{e['name']} ({e['role']})": e["id"] for e in employees}
selected = st.selectbox("Select employee", [""] + list(employee_options.keys()))

if selected and selected in employee_options:
    emp_id = employee_options[selected]
    emp = db.get_employee(emp_id)

    if emp:
        with st.form("edit_employee_form"):
            st.markdown(f"**Editing: {emp['name']}**")
            cols = st.columns([2, 1, 1])
            edit_name = cols[0].text_input("Full Name", value=emp["name"])
            edit_role = cols[1].selectbox("Role", db.ROLES, index=db.ROLES.index(emp["role"]))
            edit_salary = cols[2].number_input(
                "Monthly Salary", value=float(emp["monthly_salary"]),
                min_value=0.0, step=100.0, format="%.0f"
            )

            cols2 = st.columns([1, 1, 1, 1])
            edit_email = cols2[0].text_input("Email", value=emp["email"])
            edit_phone = cols2[1].text_input("Phone", value=emp["phone"])
            try:
                default_date = datetime.strptime(emp["hire_date"], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                default_date = date.today()
            edit_hire = cols2[2].date_input("Hire Date", value=default_date)
            edit_active = cols2[3].checkbox("Active", value=bool(emp["is_active"]))

            edit_notes = st.text_input("Notes", value=emp["notes"] or "")

            col_save, col_delete = st.columns(2)
            save = col_save.form_submit_button("Save Changes", use_container_width=True)
            delete = col_delete.form_submit_button("Delete Employee", use_container_width=True)

            if save:
                db.update_employee(
                    emp_id,
                    name=edit_name.strip(),
                    role=edit_role,
                    monthly_salary=edit_salary,
                    email=edit_email.strip(),
                    phone=edit_phone.strip(),
                    hire_date=edit_hire.strftime("%Y-%m-%d"),
                    is_active=int(edit_active),
                    notes=edit_notes.strip(),
                )
                st.success("Employee updated.")
                st.rerun()

            if delete:
                db.delete_employee(emp_id)
                st.success(f"Deleted {emp['name']}.")
                st.rerun()
