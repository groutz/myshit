"""Sample tracker daily-update I/O.

Αθανάσιος (Sakis) delivers the raw responses file from Survey Solutions — one
row per completed interview, all interviews so far (cumulative), trimmed to just
the variables needed here: an interview id, region and urbanity (and optionally
a status). This module builds that template and parses an upload into per-stratum
completes by counting the rows that fall in each region × urbanity stratum.
"""

from __future__ import annotations

import io
import unicodedata

import pandas as pd

RESP_SHEET = "Responses"

# 13 NUTS-2 regions -> code, keyed by accent-stripped lowercase name so the
# uploaded file may carry either the Greek name or the EL.. code.
REGION_CODES = {
    "αττικη": "EL30",
    "βορειο αιγαιο": "EL41",
    "νοτιο αιγαιο": "EL42",
    "κρητη": "EL43",
    "ανατολικη μακεδονια και θρακη": "EL51",
    "κεντρικη μακεδονια": "EL52",
    "δυτικη μακεδονια": "EL53",
    "ηπειρος": "EL54",
    "θεσσαλια": "EL61",
    "ιονια νησια": "EL62",
    "δυτικη ελλαδα": "EL63",
    "στερεα ελλαδα": "EL64",
    "πελοποννησος": "EL65",
}

# Survey Solutions numbers the 13 regions 1-13 in NUTS-2 code order.
REGION_NUM = {
    1: "αττικη", 2: "βορειο αιγαιο", 3: "νοτιο αιγαιο", 4: "κρητη",
    5: "ανατολικη μακεδονια και θρακη", 6: "κεντρικη μακεδονια",
    7: "δυτικη μακεδονια", 8: "ηπειρος", 9: "θεσσαλια", 10: "ιονια νησια",
    11: "δυτικη ελλαδα", 12: "στερεα ελλαδα", 13: "πελοποννησος",
}


# --------------------------------------------------------------- normalising
def _norm(s) -> str:
    s = "" if s is None else str(s)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.strip().lower()


def _urban_rural(value) -> str | None:
    n = _norm(value)
    if not n:
        return None
    # check rural first: "ημιαστικα" also contains the urban stem "αστ".
    if any(t in n for t in ("agr", "ημι", "αγρ", "rural", "semi")) or n in ("r",):
        return "Αγροτικά/Ημιαστικά"
    if "αστ" in n or "ast" in n or "urban" in n or n in ("u",):
        return "Αστικά"
    return None


def _is_complete(value) -> bool:
    n = _norm(value)
    return any(t in n for t in ("complet", "approv", "ολοκλ", "εγκ"))


def _lookups(state: dict):
    """id->row, plus (region,type)->row keyed by name, EL code and number 1-13."""
    by_id, by_rt, by_code, by_num = {}, {}, {}, {}
    num_by_name = {name: n for n, name in REGION_NUM.items()}
    for r in state.get("sample", []):
        by_id[int(r["id"])] = r
        rn, ty = _norm(r["region"]), _norm(r["type"])
        by_rt[(rn, ty)] = r
        code = REGION_CODES.get(rn)
        if code:
            by_code[(code, ty)] = r
        num = num_by_name.get(rn)
        if num:
            by_num[(num, ty)] = r
    return by_id, by_rt, by_code, by_num


def _match_stratum(region_val, type_val, lk):
    ur = _urban_rural(type_val)
    if ur is None:
        return None
    ty = _norm(ur)
    _, by_rt, by_code, by_num = lk
    row = by_rt.get((_norm(region_val), ty))
    if row:
        return row
    row = by_code.get((str(region_val).strip().upper(), ty))
    if row:
        return row
    try:                                    # numeric region code 1-13
        return by_num.get((int(float(str(region_val).strip())), ty))
    except (TypeError, ValueError):
        return None


# ------------------------------------------------------------------ template
def build_template(state: dict) -> bytes:
    """A raw-responses template (Instructions + empty Responses sheet +
    Reference list of valid region/urbanity values) for Sakis to populate."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    wb = Workbook()
    info = wb.active
    info.title = "Instructions"
    lines = [
        ("OECD/INFE 2026 — Greece · Sample daily responses", True),
        ("", False),
        ("Owner: Αθανάσιος (Sakis). Deliver every fieldwork day by 10:00.", False),
        ("", False),
        ("Provide the RAW responses data: one row per COMPLETED interview, all "
         "interviews so far (cumulative).", False),
        (f"Put the rows on the '{RESP_SHEET}' tab, keeping only these columns:", False),
        ("    • Interview ID   (optional — used to drop duplicates)", False),
        ("    • Region (NUTS-2)   — number 1-13, EL.. code, or Greek name "
         "(see Reference tab)", False),
        ("    • Urban/Rural   — Αστικά or Αγροτικά/Ημιαστικά (Urban/Rural also ok)", False),
        ("    • Status   (optional — if present, only Completed rows are counted)", False),
        ("", False),
        ("The app counts the rows in each region × urbanity stratum to get "
         "completes. Each upload REPLACES the previous counts.", False),
        ("Save and upload on the Sample page of the tracker.", False),
    ]
    for i, (txt, bold) in enumerate(lines, 1):
        c = info.cell(row=i, column=1, value=txt)
        if bold:
            c.font = Font(bold=True, size=13)
    info.column_dimensions["A"].width = 92

    head_fill = PatternFill("solid", fgColor="1A73E8")

    ws = wb.create_sheet(RESP_SHEET)
    for j, name in enumerate(["Interview ID", "Region (NUTS-2)", "Urban/Rural",
                              "Status"], 1):
        c = ws.cell(row=1, column=j, value=name)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = head_fill
        c.alignment = Alignment(horizontal="center")
    for j, w in enumerate([16, 34, 22, 14], 1):
        ws.column_dimensions[chr(64 + j)].width = w
    ws.freeze_panes = "A2"

    ref = wb.create_sheet("Reference")
    ref.cell(row=1, column=1, value="Valid Region values — use the No., the "
             "Code, or the name").font = Font(bold=True)
    ref.cell(row=2, column=1, value="No.").font = Font(bold=True)
    ref.cell(row=2, column=2, value="Region (NUTS-2)").font = Font(bold=True)
    ref.cell(row=2, column=3, value="Code").font = Font(bold=True)
    num_by_name = {name: n for n, name in REGION_NUM.items()}
    seen = []
    for r in state.get("sample", []):
        if r["region"] not in seen:
            seen.append(r["region"])
    # list in the numeric (NUTS-2 code) order
    seen.sort(key=lambda nm: num_by_name.get(_norm(nm), 99))
    for i, name in enumerate(seen, start=3):
        ref.cell(row=i, column=1, value=num_by_name.get(_norm(name), ""))
        ref.cell(row=i, column=2, value=name)
        ref.cell(row=i, column=3, value=REGION_CODES.get(_norm(name), ""))
    base = len(seen) + 4
    ref.cell(row=base, column=1, value="Valid Urban/Rural values").font = Font(bold=True)
    ref.cell(row=base + 1, column=1, value="Αστικά")
    ref.cell(row=base + 2, column=1, value="Αγροτικά/Ημιαστικά")
    ref.column_dimensions["A"].width = 6
    ref.column_dimensions["B"].width = 34
    ref.column_dimensions["C"].width = 10

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# -------------------------------------------------------------------- parsing
def _read_any(upload) -> pd.DataFrame:
    name = getattr(upload, "name", "").lower()
    if name.endswith(".csv"):
        return pd.read_csv(upload)
    xls = pd.ExcelFile(upload, engine="openpyxl")
    sheet = RESP_SHEET if RESP_SHEET in xls.sheet_names else xls.sheet_names[0]
    return xls.parse(sheet)


def _colmap(df: pd.DataFrame) -> dict:
    out = {}
    for col in df.columns:
        n = _norm(col)
        if "status" in n or "κατασ" in n:
            out["status"] = col
        elif "interview" in n or n in ("id", "case", "caseid", "key"):
            out["id"] = col
        elif "region" in n or "nuts" in n or "περιφ" in n:
            out["region"] = col
        elif "urban" in n or "rural" in n or "αστ" in n or "αγρ" in n or "αστικ" in n:
            out["type"] = col
        elif "complet" in n and "status" not in n:
            out["completes"] = col
        elif "refus" in n:
            out["refusals"] = col
        elif "call" in n:
            out["calls"] = col
    return out


def parse_upload(upload, state: dict) -> dict:
    """Return {updates, mode, warnings, counted, excluded}. Nothing is written."""
    df = _read_any(upload).dropna(how="all")
    cm = _colmap(df)
    lk = _lookups(state)
    by_id = lk[0]
    warnings: list[str] = []
    excluded = 0

    def to_int(v):
        try:
            return None if pd.isna(v) else int(round(float(v)))
        except (TypeError, ValueError):
            return None

    if "region" not in cm or "type" not in cm:
        raise ValueError("Need a Region column and an Urban/Rural column. "
                         "Found: " + ", ".join(map(str, df.columns)))

    agg: dict[int, dict] = {}

    if "completes" in cm:
        # already aggregated per stratum
        mode = "per-stratum totals"
        for _, row in df.iterrows():
            tr = (by_id.get(to_int(row[cm["id"]])) if "id" in cm else None) \
                or _match_stratum(row[cm["region"]], row[cm["type"]], lk)
            if not tr:
                warnings.append(f"Row not matched: {row[cm['region']]} / {row[cm['type']]}")
                continue
            d = agg.setdefault(int(tr["id"]), {})
            c = to_int(row[cm["completes"]])
            if c is not None:
                d["completes"] = c
            for k in ("refusals", "calls"):
                if k in cm and to_int(row[cm[k]]) is not None:
                    d[k] = to_int(row[cm[k]])
        counted = sum(v.get("completes", 0) for v in agg.values())
    else:
        # raw responses: one completed interview per row
        mode = "raw responses (counted per stratum)"
        if "id" in cm:
            df = df.drop_duplicates(subset=[cm["id"]])
        for _, row in df.iterrows():
            if "status" in cm and not _is_complete(row[cm["status"]]):
                excluded += 1
                continue
            tr = _match_stratum(row[cm["region"]], row[cm["type"]], lk)
            if not tr:
                warnings.append(f"Interview not matched: {row[cm['region']]} / "
                                f"{row[cm['type']]}")
                continue
            d = agg.setdefault(int(tr["id"]), {})
            d["completes"] = d.get("completes", 0) + 1
        counted = sum(v.get("completes", 0) for v in agg.values())

    # every stratum appears in the preview (0 if absent from the file)
    updates = []
    for sid in sorted(by_id):
        cur = by_id[sid]
        vals = agg.get(sid, {})
        updates.append({
            "id": sid, "region": cur["region"], "type": cur["type"],
            "old_completes": cur.get("completes", 0),
            "new_completes": vals.get("completes", 0),
            "new_refusals": vals.get("refusals"),
            "new_calls": vals.get("calls"),
        })
    return {"updates": updates, "mode": mode, "warnings": warnings,
            "counted": counted, "excluded": excluded}


def apply_updates(state: dict, updates: list[dict]) -> None:
    by_id = _lookups(state)[0]
    for u in updates:
        row = by_id[u["id"]]
        row["completes"] = int(u["new_completes"])
        if u.get("new_refusals") is not None:
            row["refusals"] = int(u["new_refusals"])
        if u.get("new_calls") is not None:
            row["calls"] = int(u["new_calls"])
