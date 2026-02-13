"""
Database layer for Survey Agency Project & HR Management Tool.
Uses SQLite for persistence with a clean functional API.
"""

import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agency_pm.db")

ROLES = ["Director", "Manager", "Researcher", "Field Staff"]
PROJECT_STATUSES = ["Pipeline", "Active", "Completed", "Lost", "On Hold"]
IMPLEMENTATION_METHODS = ["CAPI", "CATI", "Desk", "Online", "Mixed"]
BUDGET_CATEGORIES = ["Equipment", "Tools", "Suppliers", "Travel", "Subcontracting", "Other"]


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize database schema."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                monthly_salary REAL NOT NULL DEFAULT 0,
                email TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                hire_date TEXT DEFAULT '',
                is_active INTEGER NOT NULL DEFAULT 1,
                notes TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                client TEXT DEFAULT '',
                description TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'Pipeline',
                implementation_method TEXT DEFAULT 'Mixed',
                contract_value REAL DEFAULT 0,
                start_date TEXT DEFAULT '',
                end_date TEXT DEFAULT '',
                expected_start_date TEXT DEFAULT '',
                expected_duration_months INTEGER DEFAULT 1,
                likelihood_pct REAL DEFAULT 50,
                expected_margin_pct REAL DEFAULT 0,
                reputation_score INTEGER DEFAULT 3,
                exports_oriented INTEGER DEFAULT 0,
                director_involvement_pct REAL DEFAULT 0,
                notes TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS time_allocations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                allocation_pct REAL NOT NULL DEFAULT 0,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                UNIQUE(employee_id, project_id, year, month)
            );

            CREATE TABLE IF NOT EXISTS budget_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                amount REAL NOT NULL DEFAULT 0,
                notes TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
        """)


# ---------------------------------------------------------------------------
# Employee CRUD
# ---------------------------------------------------------------------------

def add_employee(name, role, monthly_salary, email="", phone="", hire_date="", notes=""):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO employees (name, role, monthly_salary, email, phone, hire_date, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (name, role, monthly_salary, email, phone, hire_date, notes),
        )


def get_employees(active_only=False):
    with get_db() as conn:
        if active_only:
            rows = conn.execute(
                "SELECT * FROM employees WHERE is_active = 1 ORDER BY role, name"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM employees ORDER BY is_active DESC, role, name"
            ).fetchall()
    return [dict(r) for r in rows]


def get_employee(employee_id):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM employees WHERE id = ?", (employee_id,)).fetchone()
    return dict(row) if row else None


def update_employee(employee_id, **kwargs):
    allowed = {"name", "role", "monthly_salary", "email", "phone", "hire_date", "is_active", "notes"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [employee_id]
    with get_db() as conn:
        conn.execute(f"UPDATE employees SET {set_clause} WHERE id = ?", values)


def delete_employee(employee_id):
    with get_db() as conn:
        conn.execute("DELETE FROM employees WHERE id = ?", (employee_id,))


# ---------------------------------------------------------------------------
# Project CRUD
# ---------------------------------------------------------------------------

def add_project(name, client="", description="", status="Pipeline",
                implementation_method="Mixed", contract_value=0,
                start_date="", end_date="", expected_start_date="",
                expected_duration_months=1, likelihood_pct=50,
                expected_margin_pct=0, reputation_score=3,
                exports_oriented=False, director_involvement_pct=0, notes=""):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO projects
               (name, client, description, status, implementation_method,
                contract_value, start_date, end_date, expected_start_date,
                expected_duration_months, likelihood_pct, expected_margin_pct,
                reputation_score, exports_oriented, director_involvement_pct, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, client, description, status, implementation_method,
             contract_value, start_date, end_date, expected_start_date,
             expected_duration_months, likelihood_pct, expected_margin_pct,
             reputation_score, int(exports_oriented), director_involvement_pct, notes),
        )


def get_projects(status=None):
    with get_db() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM projects WHERE status = ? ORDER BY name", (status,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM projects ORDER BY status, name").fetchall()
    return [dict(r) for r in rows]


def get_project(project_id):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    return dict(row) if row else None


def update_project(project_id, **kwargs):
    allowed = {
        "name", "client", "description", "status", "implementation_method",
        "contract_value", "start_date", "end_date", "expected_start_date",
        "expected_duration_months", "likelihood_pct", "expected_margin_pct",
        "reputation_score", "exports_oriented", "director_involvement_pct", "notes",
    }
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [project_id]
    with get_db() as conn:
        conn.execute(f"UPDATE projects SET {set_clause} WHERE id = ?", values)


def delete_project(project_id):
    with get_db() as conn:
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))


# ---------------------------------------------------------------------------
# Time Allocation
# ---------------------------------------------------------------------------

def set_allocation(employee_id, project_id, year, month, allocation_pct):
    """Set or update the allocation for an employee on a project for a given month."""
    with get_db() as conn:
        if allocation_pct <= 0:
            conn.execute(
                """DELETE FROM time_allocations
                   WHERE employee_id = ? AND project_id = ? AND year = ? AND month = ?""",
                (employee_id, project_id, year, month),
            )
        else:
            conn.execute(
                """INSERT INTO time_allocations (employee_id, project_id, year, month, allocation_pct)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(employee_id, project_id, year, month)
                   DO UPDATE SET allocation_pct = excluded.allocation_pct""",
                (employee_id, project_id, year, month, allocation_pct),
            )


def get_allocations_for_month(year, month):
    """Get all allocations for a given month with employee and project details."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT ta.*, e.name as employee_name, e.role as employee_role,
                      e.monthly_salary, p.name as project_name
               FROM time_allocations ta
               JOIN employees e ON ta.employee_id = e.id
               JOIN projects p ON ta.project_id = p.id
               WHERE ta.year = ? AND ta.month = ?
               ORDER BY e.name, p.name""",
            (year, month),
        ).fetchall()
    return [dict(r) for r in rows]


def get_employee_total_allocation(employee_id, year, month):
    """Get total allocation percentage for an employee in a given month."""
    with get_db() as conn:
        row = conn.execute(
            """SELECT COALESCE(SUM(allocation_pct), 0) as total
               FROM time_allocations
               WHERE employee_id = ? AND year = ? AND month = ?""",
            (employee_id, year, month),
        ).fetchone()
    return row["total"]


def get_project_personnel_costs(project_id, year=None, month=None):
    """Get personnel costs for a project, optionally filtered by month."""
    with get_db() as conn:
        query = """
            SELECT ta.year, ta.month, ta.allocation_pct,
                   e.id as employee_id, e.name as employee_name,
                   e.role as employee_role, e.monthly_salary,
                   (e.monthly_salary * ta.allocation_pct / 100.0) as cost
            FROM time_allocations ta
            JOIN employees e ON ta.employee_id = e.id
            WHERE ta.project_id = ?
        """
        params = [project_id]
        if year is not None:
            query += " AND ta.year = ?"
            params.append(year)
        if month is not None:
            query += " AND ta.month = ?"
            params.append(month)
        query += " ORDER BY ta.year, ta.month, e.name"
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def get_project_total_personnel_cost(project_id):
    """Get total personnel cost across all months for a project."""
    with get_db() as conn:
        row = conn.execute(
            """SELECT COALESCE(SUM(e.monthly_salary * ta.allocation_pct / 100.0), 0) as total
               FROM time_allocations ta
               JOIN employees e ON ta.employee_id = e.id
               WHERE ta.project_id = ?""",
            (project_id,),
        ).fetchone()
    return row["total"]


# ---------------------------------------------------------------------------
# Budget Items
# ---------------------------------------------------------------------------

def add_budget_item(project_id, category, description, amount, notes=""):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO budget_items (project_id, category, description, amount, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (project_id, category, description, amount, notes),
        )


def get_budget_items(project_id):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM budget_items WHERE project_id = ? ORDER BY category, description",
            (project_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_budget_total(project_id):
    with get_db() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) as total FROM budget_items WHERE project_id = ?",
            (project_id,),
        ).fetchone()
    return row["total"]


def update_budget_item(item_id, **kwargs):
    allowed = {"category", "description", "amount", "notes"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [item_id]
    with get_db() as conn:
        conn.execute(f"UPDATE budget_items SET {set_clause} WHERE id = ?", values)


def delete_budget_item(item_id):
    with get_db() as conn:
        conn.execute("DELETE FROM budget_items WHERE id = ?", (item_id,))


# ---------------------------------------------------------------------------
# Analytics & Reporting
# ---------------------------------------------------------------------------

def get_employee_utilization(year, month):
    """Get utilization (total allocation %) for all active employees in a month."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT e.id, e.name, e.role, e.monthly_salary,
                      COALESCE(SUM(ta.allocation_pct), 0) as total_allocation
               FROM employees e
               LEFT JOIN time_allocations ta
                   ON e.id = ta.employee_id AND ta.year = ? AND ta.month = ?
               WHERE e.is_active = 1
               GROUP BY e.id
               ORDER BY e.role, e.name""",
            (year, month),
        ).fetchall()
    return [dict(r) for r in rows]


def get_pipeline_summary():
    """Get summary of pipeline projects with weighted values."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT *,
                      (contract_value * likelihood_pct / 100.0) as weighted_value,
                      (contract_value * likelihood_pct / 100.0 * expected_margin_pct / 100.0) as weighted_profit
               FROM projects
               WHERE status = 'Pipeline'
               ORDER BY likelihood_pct DESC, contract_value DESC"""
        ).fetchall()
    return [dict(r) for r in rows]


def get_monthly_revenue_forecast(start_year, start_month, num_months=12):
    """
    Build a monthly revenue forecast from pipeline and active projects.
    Revenue is spread evenly across expected_duration_months from expected_start_date.
    """
    projects = get_projects()
    forecast = {}

    for proj in projects:
        if proj["status"] in ("Lost", "Completed"):
            continue

        contract_value = proj["contract_value"] or 0
        duration = proj["expected_duration_months"] or 1
        likelihood = proj["likelihood_pct"] if proj["status"] == "Pipeline" else 100
        margin_pct = proj["expected_margin_pct"] or 0
        director_pct = proj["director_involvement_pct"] or 0

        # Determine start date for revenue recognition
        if proj["status"] == "Active" and proj["start_date"]:
            try:
                sd = datetime.strptime(proj["start_date"], "%Y-%m-%d").date()
            except ValueError:
                continue
        elif proj["expected_start_date"]:
            try:
                sd = datetime.strptime(proj["expected_start_date"], "%Y-%m-%d").date()
            except ValueError:
                continue
        else:
            continue

        monthly_revenue = contract_value / duration
        weighted_revenue = monthly_revenue * likelihood / 100.0
        weighted_profit = weighted_revenue * margin_pct / 100.0
        monthly_director = director_pct

        for i in range(duration):
            m = sd.month + i
            y = sd.year + (m - 1) // 12
            m = ((m - 1) % 12) + 1
            key = (y, m)

            if key not in forecast:
                forecast[key] = {
                    "year": y, "month": m,
                    "revenue": 0, "weighted_revenue": 0,
                    "profit": 0, "weighted_profit": 0,
                    "director_involvement": 0, "project_count": 0,
                }

            forecast[key]["revenue"] += monthly_revenue
            forecast[key]["weighted_revenue"] += weighted_revenue
            forecast[key]["profit"] += monthly_revenue * margin_pct / 100.0
            forecast[key]["weighted_profit"] += weighted_profit
            forecast[key]["director_involvement"] += monthly_director
            forecast[key]["project_count"] += 1

    # Filter to requested window and sort
    result = []
    for i in range(num_months):
        m = start_month + i
        y = start_year + (m - 1) // 12
        m = ((m - 1) % 12) + 1
        key = (y, m)
        if key in forecast:
            result.append(forecast[key])
        else:
            result.append({
                "year": y, "month": m,
                "revenue": 0, "weighted_revenue": 0,
                "profit": 0, "weighted_profit": 0,
                "director_involvement": 0, "project_count": 0,
            })

    return result


def get_project_margin(project_id):
    """Calculate full project margin: revenue - personnel costs - budget items."""
    proj = get_project(project_id)
    if not proj:
        return None

    revenue = proj["contract_value"] or 0
    personnel_cost = get_project_total_personnel_cost(project_id)
    non_personnel_cost = get_budget_total(project_id)
    total_cost = personnel_cost + non_personnel_cost
    margin = revenue - total_cost
    margin_pct = (margin / revenue * 100) if revenue > 0 else 0

    return {
        "revenue": revenue,
        "personnel_cost": personnel_cost,
        "non_personnel_cost": non_personnel_cost,
        "total_cost": total_cost,
        "margin": margin,
        "margin_pct": margin_pct,
    }


def get_all_project_margins():
    """Get margin summary for all active/pipeline projects."""
    projects = get_projects()
    results = []
    for proj in projects:
        if proj["status"] in ("Lost",):
            continue
        margin = get_project_margin(proj["id"])
        if margin:
            margin["project_id"] = proj["id"]
            margin["project_name"] = proj["name"]
            margin["client"] = proj["client"]
            margin["status"] = proj["status"]
            results.append(margin)
    return results


def get_director_capacity(year, month):
    """Get director allocation summary for a given month."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT e.id, e.name,
                      COALESCE(SUM(ta.allocation_pct), 0) as total_allocation
               FROM employees e
               LEFT JOIN time_allocations ta
                   ON e.id = ta.employee_id AND ta.year = ? AND ta.month = ?
               WHERE e.role = 'Director' AND e.is_active = 1
               GROUP BY e.id
               ORDER BY e.name""",
            (year, month),
        ).fetchall()
    return [dict(r) for r in rows]


def seed_demo_data():
    """Insert demo data for testing."""
    employees = get_employees()
    if employees:
        return  # Already has data

    # Demo employees
    demo_employees = [
        ("Maria Papadopoulou", "Director", 6000, "maria@agency.com", "", "2015-03-01"),
        ("Nikos Georgiou", "Director", 5500, "nikos@agency.com", "", "2016-06-15"),
        ("Elena Konstantinou", "Manager", 3500, "elena@agency.com", "", "2018-01-10"),
        ("Dimitris Alexiou", "Manager", 3200, "dimitris@agency.com", "", "2019-04-01"),
        ("Anna Petrova", "Researcher", 2200, "anna@agency.com", "", "2020-09-01"),
        ("Kostas Nikolaou", "Researcher", 2000, "kostas@agency.com", "", "2021-02-15"),
        ("Sofia Ioannou", "Researcher", 2100, "sofia@agency.com", "", "2020-11-01"),
        ("Yannis Dimitriou", "Field Staff", 1500, "yannis@agency.com", "", "2022-01-10"),
        ("Christina Vasileiou", "Field Staff", 1400, "christina@agency.com", "", "2022-03-20"),
        ("Petros Mavridis", "Field Staff", 1500, "petros@agency.com", "", "2021-08-01"),
        ("Ioanna Karamanli", "Field Staff", 1350, "ioanna@agency.com", "", "2023-01-15"),
        ("Alexandros Tsiolis", "Researcher", 2300, "alex@agency.com", "", "2019-07-01"),
    ]
    for name, role, salary, email, phone, hire_date in demo_employees:
        add_employee(name, role, salary, email, phone, hire_date)

    # Demo projects
    demo_projects = [
        ("Consumer Confidence Survey Q1", "Ministry of Economy", "Quarterly consumer confidence tracking",
         "Active", "CATI", 45000, "2026-01-15", "2026-03-31", "", 3, 100, 35, 4, False, 15),
        ("Tourism Satisfaction Study", "National Tourism Board", "Annual tourist satisfaction survey",
         "Active", "CAPI", 85000, "2026-01-01", "2026-06-30", "", 6, 100, 28, 5, True, 20),
        ("Employee Engagement Survey", "Alpha Bank", "Internal employee engagement assessment",
         "Active", "Online", 22000, "2026-02-01", "2026-03-15", "", 2, 100, 45, 3, False, 10),
        ("EU Barometer Wave 12", "European Commission", "Eurobarometer public opinion survey",
         "Pipeline", "CAPI", 120000, "", "", "2026-04-01", 4, 75, 22, 5, True, 25),
        ("Product Testing - New Beverage", "CocaCola HBC", "Blind taste test for new product line",
         "Pipeline", "CAPI", 35000, "", "", "2026-03-15", 2, 85, 40, 3, False, 10),
        ("Healthcare Access Study", "WHO Regional", "Access to healthcare in rural areas",
         "Pipeline", "Mixed", 95000, "", "", "2026-05-01", 5, 60, 25, 5, True, 20),
        ("Political Opinion Poll", "Media Group Alpha", "Pre-election opinion polling",
         "Pipeline", "CATI", 18000, "", "", "2026-03-01", 1, 90, 50, 4, False, 15),
        ("Brand Tracking Wave 8", "Vodafone", "Continuous brand health tracking",
         "Active", "Online", 30000, "2026-02-01", "2026-04-30", "", 3, 100, 38, 3, False, 10),
        ("Social Cohesion Index", "UNDP", "National social cohesion measurement",
         "Pipeline", "Mixed", 150000, "", "", "2026-06-01", 8, 40, 20, 5, True, 30),
        ("Customer Satisfaction - Telco", "OTE Group", "Annual CSAT for telecom provider",
         "Completed", "CATI", 28000, "2025-10-01", "2025-12-31", "", 3, 100, 42, 3, False, 10),
    ]
    for (name, client, desc, status, method, value, sd, ed, esd,
         dur, like, margin, rep, exports, director) in demo_projects:
        add_project(name, client, desc, status, method, value, sd, ed, esd,
                    dur, like, margin, rep, exports, director)

    # Demo time allocations (current month: Feb 2026)
    # Get IDs
    employees = get_employees()
    projects = get_projects()
    emp_map = {e["name"]: e["id"] for e in employees}
    proj_map = {p["name"]: p["id"] for p in projects}

    allocations = [
        # Directors
        ("Maria Papadopoulou", "Consumer Confidence Survey Q1", 2026, 2, 15),
        ("Maria Papadopoulou", "Tourism Satisfaction Study", 2026, 2, 20),
        ("Maria Papadopoulou", "Employee Engagement Survey", 2026, 2, 10),
        ("Nikos Georgiou", "Tourism Satisfaction Study", 2026, 2, 15),
        ("Nikos Georgiou", "Brand Tracking Wave 8", 2026, 2, 10),
        # Managers
        ("Elena Konstantinou", "Consumer Confidence Survey Q1", 2026, 2, 40),
        ("Elena Konstantinou", "Employee Engagement Survey", 2026, 2, 30),
        ("Dimitris Alexiou", "Tourism Satisfaction Study", 2026, 2, 50),
        ("Dimitris Alexiou", "Brand Tracking Wave 8", 2026, 2, 30),
        # Researchers
        ("Anna Petrova", "Consumer Confidence Survey Q1", 2026, 2, 60),
        ("Anna Petrova", "Employee Engagement Survey", 2026, 2, 30),
        ("Kostas Nikolaou", "Tourism Satisfaction Study", 2026, 2, 80),
        ("Sofia Ioannou", "Brand Tracking Wave 8", 2026, 2, 50),
        ("Sofia Ioannou", "Consumer Confidence Survey Q1", 2026, 2, 30),
        ("Alexandros Tsiolis", "Tourism Satisfaction Study", 2026, 2, 40),
        ("Alexandros Tsiolis", "Employee Engagement Survey", 2026, 2, 40),
        # Field Staff
        ("Yannis Dimitriou", "Consumer Confidence Survey Q1", 2026, 2, 70),
        ("Yannis Dimitriou", "Tourism Satisfaction Study", 2026, 2, 30),
        ("Christina Vasileiou", "Tourism Satisfaction Study", 2026, 2, 100),
        ("Petros Mavridis", "Consumer Confidence Survey Q1", 2026, 2, 50),
        ("Petros Mavridis", "Brand Tracking Wave 8", 2026, 2, 50),
        ("Ioanna Karamanli", "Tourism Satisfaction Study", 2026, 2, 60),
        ("Ioanna Karamanli", "Employee Engagement Survey", 2026, 2, 20),
    ]
    for emp_name, proj_name, y, m, pct in allocations:
        if emp_name in emp_map and proj_name in proj_map:
            set_allocation(emp_map[emp_name], proj_map[proj_name], y, m, pct)

    # Also add January allocations (slightly different)
    jan_allocations = [
        ("Maria Papadopoulou", "Consumer Confidence Survey Q1", 2026, 1, 20),
        ("Maria Papadopoulou", "Tourism Satisfaction Study", 2026, 1, 15),
        ("Nikos Georgiou", "Tourism Satisfaction Study", 2026, 1, 20),
        ("Elena Konstantinou", "Consumer Confidence Survey Q1", 2026, 1, 50),
        ("Dimitris Alexiou", "Tourism Satisfaction Study", 2026, 1, 60),
        ("Anna Petrova", "Consumer Confidence Survey Q1", 2026, 1, 70),
        ("Kostas Nikolaou", "Tourism Satisfaction Study", 2026, 1, 90),
        ("Sofia Ioannou", "Consumer Confidence Survey Q1", 2026, 1, 40),
        ("Alexandros Tsiolis", "Tourism Satisfaction Study", 2026, 1, 50),
        ("Yannis Dimitriou", "Consumer Confidence Survey Q1", 2026, 1, 80),
        ("Christina Vasileiou", "Tourism Satisfaction Study", 2026, 1, 100),
        ("Petros Mavridis", "Consumer Confidence Survey Q1", 2026, 1, 60),
        ("Ioanna Karamanli", "Tourism Satisfaction Study", 2026, 1, 70),
    ]
    for emp_name, proj_name, y, m, pct in jan_allocations:
        if emp_name in emp_map and proj_name in proj_map:
            set_allocation(emp_map[emp_name], proj_map[proj_name], y, m, pct)

    # Demo budget items
    budget_items = [
        ("Consumer Confidence Survey Q1", "Equipment", "CATI software licenses (3 months)", 2400),
        ("Consumer Confidence Survey Q1", "Tools", "Survey platform subscription", 800),
        ("Consumer Confidence Survey Q1", "Suppliers", "Sample provider", 3500),
        ("Tourism Satisfaction Study", "Equipment", "Tablets for CAPI (rental)", 4200),
        ("Tourism Satisfaction Study", "Travel", "Fieldwork travel - islands", 8500),
        ("Tourism Satisfaction Study", "Suppliers", "Translation services (5 languages)", 6000),
        ("Tourism Satisfaction Study", "Tools", "Survey platform + GPS tracking", 1500),
        ("Employee Engagement Survey", "Tools", "Online survey platform", 500),
        ("Employee Engagement Survey", "Suppliers", "Email distribution service", 200),
        ("Brand Tracking Wave 8", "Tools", "Online panel access", 4500),
        ("Brand Tracking Wave 8", "Suppliers", "Data processing partner", 2000),
    ]
    for proj_name, category, description, amount in budget_items:
        if proj_name in proj_map:
            add_budget_item(proj_map[proj_name], category, description, amount)
