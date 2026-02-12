"""
Project Management Page
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date

import database as db
from theme import apply_theme

db.init_db()

st.set_page_config(page_title="Projects - Survey Agency PM", layout="wide")
apply_theme()
st.title("Project Management")

# --- Add Project ---
with st.expander("Add New Project", expanded=False):
    with st.form("add_project_form"):
        cols = st.columns([2, 2, 1])
        name = cols[0].text_input("Project Name*")
        client = cols[1].text_input("Client")
        status = cols[2].selectbox("Status", db.PROJECT_STATUSES)

        cols2 = st.columns([1, 1, 1, 1])
        method = cols2[0].selectbox("Implementation Method", db.IMPLEMENTATION_METHODS)
        contract_value = cols2[1].number_input("Contract Value", min_value=0.0, step=1000.0, format="%.0f")
        likelihood = cols2[2].slider("Likelihood of Winning (%)", 0, 100, 50)
        margin_pct = cols2[3].number_input("Expected Margin %", min_value=-100.0, max_value=100.0, value=25.0, step=1.0)

        cols3 = st.columns([1, 1, 1, 1])
        start_date = cols3[0].date_input("Start Date", value=None)
        end_date = cols3[1].date_input("End Date", value=None)
        expected_start = cols3[2].date_input("Expected Start (Pipeline)", value=None)
        duration = cols3[3].number_input("Expected Duration (months)", min_value=1, max_value=36, value=3)

        cols4 = st.columns([1, 1, 1, 1])
        reputation = cols4[0].slider("Reputation Score", 1, 5, 3)
        exports = cols4[1].checkbox("Exports-Oriented")
        director_inv = cols4[2].number_input("Director Involvement %", min_value=0.0, max_value=100.0, value=10.0, step=5.0)

        description = st.text_area("Description", height=80)
        notes = st.text_input("Notes")

        submitted = st.form_submit_button("Add Project", use_container_width=True)
        if submitted:
            if not name.strip():
                st.error("Project name is required.")
            else:
                db.add_project(
                    name=name.strip(),
                    client=client.strip(),
                    description=description.strip(),
                    status=status,
                    implementation_method=method,
                    contract_value=contract_value,
                    start_date=start_date.strftime("%Y-%m-%d") if start_date else "",
                    end_date=end_date.strftime("%Y-%m-%d") if end_date else "",
                    expected_start_date=expected_start.strftime("%Y-%m-%d") if expected_start else "",
                    expected_duration_months=duration,
                    likelihood_pct=likelihood,
                    expected_margin_pct=margin_pct,
                    reputation_score=reputation,
                    exports_oriented=exports,
                    director_involvement_pct=director_inv,
                    notes=notes.strip(),
                )
                st.success(f"Added project: {name}")
                st.rerun()

st.divider()

# --- Filters ---
col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
status_filter = col_f1.multiselect("Filter by Status", db.PROJECT_STATUSES, default=[])
method_filter = col_f2.multiselect("Filter by Method", db.IMPLEMENTATION_METHODS, default=[])

# --- Project List ---
all_projects = db.get_projects()
projects = all_projects
if status_filter:
    projects = [p for p in projects if p["status"] in status_filter]
if method_filter:
    projects = [p for p in projects if p["implementation_method"] in method_filter]

if not projects:
    st.info("No projects found. Add one above or adjust filters.")
    st.stop()

st.subheader(f"Projects ({len(projects)})")

rows = []
for p in projects:
    margin_data = db.get_project_margin(p["id"])
    rows.append({
        "ID": p["id"],
        "Name": p["name"],
        "Client": p["client"],
        "Status": p["status"],
        "Method": p["implementation_method"],
        "Contract Value": p["contract_value"],
        "Likelihood": f"{p['likelihood_pct']:.0f}%" if p["status"] == "Pipeline" else "-",
        "Margin %": f"{margin_data['margin_pct']:.1f}%" if margin_data else "-",
        "Reputation": p["reputation_score"],
        "Exports": "Yes" if p["exports_oriented"] else "No",
    })

df = pd.DataFrame(rows)
st.dataframe(
    df.style.format({"Contract Value": "{:,.0f}"}),
    use_container_width=True,
    hide_index=True,
)

# --- Summary ---
st.divider()
total_value = sum(p["contract_value"] for p in projects)
active_value = sum(p["contract_value"] for p in projects if p["status"] == "Active")
pipeline_weighted = sum(
    p["contract_value"] * p["likelihood_pct"] / 100
    for p in projects if p["status"] == "Pipeline"
)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Projects", len(projects))
m2.metric("Total Contract Value", f"{total_value:,.0f}")
m3.metric("Active Value", f"{active_value:,.0f}")
m4.metric("Pipeline (Weighted)", f"{pipeline_weighted:,.0f}")

# --- Edit Project ---
st.divider()
st.subheader("Edit or Remove Project")

project_options = {f"{p['name']} ({p['status']})": p["id"] for p in projects}
selected = st.selectbox("Select project", [""] + list(project_options.keys()))

if selected and selected in project_options:
    proj_id = project_options[selected]
    proj = db.get_project(proj_id)

    if proj:
        with st.form("edit_project_form"):
            st.markdown(f"**Editing: {proj['name']}**")

            cols = st.columns([2, 2, 1])
            edit_name = cols[0].text_input("Project Name", value=proj["name"])
            edit_client = cols[1].text_input("Client", value=proj["client"])
            edit_status = cols[2].selectbox(
                "Status", db.PROJECT_STATUSES,
                index=db.PROJECT_STATUSES.index(proj["status"])
            )

            cols2 = st.columns([1, 1, 1, 1])
            edit_method = cols2[0].selectbox(
                "Method", db.IMPLEMENTATION_METHODS,
                index=db.IMPLEMENTATION_METHODS.index(proj["implementation_method"])
                if proj["implementation_method"] in db.IMPLEMENTATION_METHODS else 0
            )
            edit_value = cols2[1].number_input(
                "Contract Value", value=float(proj["contract_value"]),
                min_value=0.0, step=1000.0, format="%.0f"
            )
            edit_likelihood = cols2[2].slider(
                "Likelihood %", 0, 100, int(proj["likelihood_pct"])
            )
            edit_margin = cols2[3].number_input(
                "Expected Margin %",
                value=float(proj["expected_margin_pct"]),
                min_value=-100.0, max_value=100.0, step=1.0
            )

            cols3 = st.columns([1, 1, 1, 1])
            try:
                sd = datetime.strptime(proj["start_date"], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                sd = None
            try:
                ed = datetime.strptime(proj["end_date"], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                ed = None
            try:
                esd = datetime.strptime(proj["expected_start_date"], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                esd = None

            edit_start = cols3[0].date_input("Start Date", value=sd)
            edit_end = cols3[1].date_input("End Date", value=ed)
            edit_exp_start = cols3[2].date_input("Expected Start", value=esd)
            edit_duration = cols3[3].number_input(
                "Duration (months)", value=int(proj["expected_duration_months"]),
                min_value=1, max_value=36
            )

            cols4 = st.columns([1, 1, 1, 1])
            edit_reputation = cols4[0].slider("Reputation", 1, 5, int(proj["reputation_score"]))
            edit_exports = cols4[1].checkbox("Exports-Oriented", value=bool(proj["exports_oriented"]))
            edit_director = cols4[2].number_input(
                "Director Involvement %",
                value=float(proj["director_involvement_pct"]),
                min_value=0.0, max_value=100.0, step=5.0
            )

            edit_desc = st.text_area("Description", value=proj["description"] or "", height=80)
            edit_notes = st.text_input("Notes", value=proj["notes"] or "")

            col_save, col_delete = st.columns(2)
            save = col_save.form_submit_button("Save Changes", use_container_width=True)
            delete = col_delete.form_submit_button("Delete Project", use_container_width=True)

            if save:
                db.update_project(
                    proj_id,
                    name=edit_name.strip(),
                    client=edit_client.strip(),
                    description=edit_desc.strip(),
                    status=edit_status,
                    implementation_method=edit_method,
                    contract_value=edit_value,
                    start_date=edit_start.strftime("%Y-%m-%d") if edit_start else "",
                    end_date=edit_end.strftime("%Y-%m-%d") if edit_end else "",
                    expected_start_date=edit_exp_start.strftime("%Y-%m-%d") if edit_exp_start else "",
                    expected_duration_months=edit_duration,
                    likelihood_pct=edit_likelihood,
                    expected_margin_pct=edit_margin,
                    reputation_score=edit_reputation,
                    exports_oriented=int(edit_exports),
                    director_involvement_pct=edit_director,
                    notes=edit_notes.strip(),
                )
                st.success("Project updated.")
                st.rerun()

            if delete:
                db.delete_project(proj_id)
                st.success(f"Deleted {proj['name']}.")
                st.rerun()
