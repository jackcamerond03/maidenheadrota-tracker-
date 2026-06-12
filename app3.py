"""
Maidenhead Rota Tracker
-----------------------
A Streamlit rota for Absolutely Karting (Maidenhead). No plotly dependency —
uses HTML/CSS for timelines. Data lives in a local SQLite file (rota.db).

Run with:  streamlit run app.py
"""

import os
import sqlite3
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

# Absolutely Karting logo, embedded so there is no separate file to deploy.
LOGO_B64 = "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"

# --------------------------------------------------------------------------- #
# CONFIGURATION
# --------------------------------------------------------------------------- #
DB_PATH = "rota.db"
LEGACY_CSV = "rota_database.csv"

DEFAULT_STAFF = {
    "Adam Mitchell": "Centre Manager", "Ella Hunter": "Assistant Manager", "Emily Smith": "Assistant Manager",
    "Brandon Brind-Winnen": "Duty Manager", "Jack Davidson": "Head Marshal", "Adam Howling": "Head Marshal",
    "James Shanks": "Head Marshal", "Willow Phillips": "Mechanic", "Alex Callaby": "Track Marshal",
    "Amelia Phillips": "Track Marshal", "Anna Larionova": "Track Marshal", "Deolu Adesanya": "Track Marshal",
    "Dilraj Rooprai": "Track Marshal", "Elizabeth Province": "Track Marshal", "Ethan Hunting": "Track Marshal",
    "Isaac Bartlett": "Track Marshal", "Marcus King": "Track Marshal", "Max King": "Track Marshal",
    "Noah Hunter": "Track Marshal", "Red Brill": "Track Marshal", "Rueben Bharj": "Track Marshal",
    "Sam Daly": "Track Marshal", "Samuel Holliday": "Track Marshal", "Sophie McDonnell": "Track Marshal",
    "Tapas Ramavarma": "Track Marshal", "Teoni Green": "Track Marshal", "Unassigned": "Unassigned",
}
DEFAULT_FIRST_AID = [
    "Adam Mitchell", "Ella Hunter", "Emily Smith", "Brandon Brind-Winnen", "Jack Davidson",
    "Elizabeth Province", "Amelia Phillips", "Samuel Holliday", "Dilraj Rooprai", "Red Brill", "Max King",
]

ROLE_ORDER_HIERARCHY = ["Centre Manager", "Assistant Manager", "Duty Manager", "Head Marshal", "Mechanic", "Track Marshal", "Unassigned"]
MANAGEMENT_ROLES = ["Centre Manager", "Assistant Manager", "Duty Manager"]

ROLE_COLORS = {
    "Centre Manager": "#1F3A5F",
    "Assistant Manager": "#6C5CE7",
    "Duty Manager": "#16A085",
    "Head Marshal": "#2980B9",
    "Mechanic": "#C0392B",
    "Track Marshal": "#E67E22",
    "Unassigned": "#95A5A6",
}

# Coverage minimums per scheduled day. Edit to match your operating policy.
MIN_FIRST_AIDERS = 1
MIN_MANAGERS = 1

OPEN_TIME = "08:00"
CLOSE_TIME = "22:00"

# 15-minute scheduling grid.
TIME_CHOICES = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 15, 30, 45)]

HOLIDAYS = [
    {"name": "May Half Term", "start": "2026-05-25", "end": "2026-05-29"},
    {"name": "Summer", "start": "2026-07-23", "end": "2026-08-31"},
    {"name": "October Half Term", "start": "2026-10-26", "end": "2026-10-30"},
]


# --------------------------------------------------------------------------- #
# DATA LAYER (SQLite)
# --------------------------------------------------------------------------- #
def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _connect()
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS shifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee TEXT NOT NULL,
                role TEXT NOT NULL,
                shift_date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS staff (
                name TEXT PRIMARY KEY,
                role TEXT NOT NULL,
                first_aid INTEGER NOT NULL DEFAULT 0
            )"""
        )
        if conn.execute("SELECT COUNT(*) FROM staff").fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO staff (name, role, first_aid) VALUES (?, ?, ?)",
                [(n, r, 1 if n in DEFAULT_FIRST_AID else 0) for n, r in DEFAULT_STAFF.items()],
            )
        if conn.execute("SELECT COUNT(*) FROM shifts").fetchone()[0] == 0 and os.path.exists(LEGACY_CSV):
            try:
                old = pd.read_csv(LEGACY_CSV)
                conn.executemany(
                    "INSERT INTO shifts (employee, role, shift_date, start_time, end_time) VALUES (?,?,?,?,?)",
                    [(str(r["Employee"]), str(r["Role"]), str(r["Date"]), str(r["Start"]), str(r["End"]))
                     for _, r in old.iterrows()],
                )
            except Exception:
                pass
        conn.commit()
    finally:
        conn.close()


def load_shifts():
    conn = _connect()
    try:
        return pd.read_sql_query(
            "SELECT id, employee AS Employee, role AS Role, shift_date AS Date, "
            "start_time AS Start, end_time AS End FROM shifts",
            conn,
        )
    finally:
        conn.close()


def load_staff():
    conn = _connect()
    try:
        return pd.read_sql_query("SELECT name, role, first_aid FROM staff ORDER BY name", conn)
    finally:
        conn.close()


def add_shift(employee, role, d, start, end):
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO shifts (employee, role, shift_date, start_time, end_time) VALUES (?,?,?,?,?)",
            (employee, role, d, start, end),
        )
        conn.commit()
    finally:
        conn.close()


def update_shift(shift_id, start, end):
    conn = _connect()
    try:
        conn.execute("UPDATE shifts SET start_time=?, end_time=? WHERE id=?", (start, end, shift_id))
        conn.commit()
    finally:
        conn.close()


def delete_shift(shift_id):
    conn = _connect()
    try:
        conn.execute("DELETE FROM shifts WHERE id=?", (shift_id,))
        conn.commit()
    finally:
        conn.close()


def upsert_staff(name, role, first_aid):
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO staff (name, role, first_aid) VALUES (?,?,?) "
            "ON CONFLICT(name) DO UPDATE SET role=excluded.role, first_aid=excluded.first_aid",
            (name, role, 1 if first_aid else 0),
        )
        conn.commit()
    finally:
        conn.close()


def replace_all_shifts(rows):
    conn = _connect()
    try:
        conn.execute("DELETE FROM shifts")
        conn.executemany(
            "INSERT INTO shifts (employee, role, shift_date, start_time, end_time) VALUES (?,?,?,?,?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# HELPERS
# --------------------------------------------------------------------------- #
def to_minutes(hhmm):
    try:
        h, m = str(hhmm).split(":")
        return int(h) * 60 + int(m)
    except Exception:
        return -1


def duration_hours(start, end):
    mins = to_minutes(end) - to_minutes(start)
    return round(mins / 60, 2) if mins > 0 else 0.0


def safe_index(value, options, default=0):
    try:
        return options.index(value)
    except (ValueError, TypeError):
        return default


def shifts_overlap(s1, e1, s2, e2):
    return to_minutes(s1) < to_minutes(e2) and to_minutes(s2) < to_minutes(e1)


def has_conflict(df, employee, d, start, end, exclude_id=None):
    same = df[(df["Employee"] == employee) & (df["Date"] == d)]
    for _, r in same.iterrows():
        if exclude_id is not None and int(r["id"]) == int(exclude_id):
            continue
        if shifts_overlap(start, end, r["Start"], r["End"]):
            return True
    return False


def coverage_shortfalls(day_df, first_aiders):
    n_fa = day_df["Employee"].isin(first_aiders).sum()
    n_mgmt = day_df["Role"].isin(MANAGEMENT_ROLES).sum()
    out = []
    if n_fa < MIN_FIRST_AIDERS:
        out.append(f"first aiders ({n_fa}/{MIN_FIRST_AIDERS})")
    if n_mgmt < MIN_MANAGERS:
        out.append(f"management ({n_mgmt}/{MIN_MANAGERS})")
    return out


def get_holiday(d):
    for h in HOLIDAYS:
        if h["start"] <= d <= h["end"]:
            return h["name"]
    return None


def build_timeline_html(df):
    """Build a simple HTML/CSS timeline (no plotly)."""
    if df.empty:
        return ""

    open_mins = to_minutes(OPEN_TIME)
    close_mins = to_minutes(CLOSE_TIME)
    span_mins = close_mins - open_mins

    employees = sorted(df["Employee"].unique())

    html = '<div style="border:1px solid #e6e8eb; border-radius:10px; padding:1rem; background:#fff; overflow-x:auto;">'
    html += '<div style="display:flex; font-family:system-ui; font-size:13px; color:#2c3e50;">'

    html += '<div style="flex:0 0 140px; padding-right:1rem; padding-bottom:0.5rem;">&nbsp;</div>'
    for h in range(int(OPEN_TIME.split(":")[0]), int(CLOSE_TIME.split(":")[0]) + 1):
        html += f'<div style="flex:1; text-align:center; font-weight:600; color:#5c6a79; font-size:11px;">{h:02d}:00</div>'
    html += '</div>'

    for emp in employees:
        emp_shifts = df[df["Employee"] == emp]
        html += '<div style="display:flex; border-top:1px solid #f0f0f0; align-items:center;">'
        html += f'<div style="flex:0 0 140px; padding:0.7rem 1rem 0.7rem 0; font-weight:600; color:#2c3e50; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{emp}</div>'

        bars_html = '<div style="flex:1; display:flex; position:relative; height:50px; gap:0.2rem;">'
        for _, shift in emp_shifts.iterrows():
            start_mins = to_minutes(shift["Start"])
            end_mins = to_minutes(shift["End"])
            if start_mins < open_mins:
                start_mins = open_mins
            if end_mins > close_mins:
                end_mins = close_mins

            left_pct = ((start_mins - open_mins) / span_mins) * 100 if span_mins > 0 else 0
            width_pct = (max(0, (end_mins - start_mins)) / span_mins) * 100 if span_mins > 0 else 0

            role = shift["Role"]
            color = ROLE_COLORS.get(role, "#95a5a6")
            start_time = shift["Start"]
            end_time = shift["End"]
            bars_html += (
                f'<div style="position:absolute; left:{left_pct}%; width:{width_pct}%; '
                f'height:100%; background:{color}; border-radius:4px; '
                f'display:flex; align-items:center; justify-content:center; '
                f'font-size:10px; color:white; font-weight:600; '
                f'border:1px solid {color}; box-shadow:0 1px 2px rgba(0,0,0,0.1);" '
                f'title="{emp} ({start_time}-{end_time}, {role})">'
                f'{start_time}-{end_time}</div>'
            )
        bars_html += '</div>'
        html += bars_html
        html += '</div>'

    html += '</div>'
    return html


# --------------------------------------------------------------------------- #
# PAGE SETUP
# --------------------------------------------------------------------------- #
st.set_page_config(layout="wide", page_title="Maidenhead Rota Tracker", page_icon="🏎️")
st.markdown(
    """<style>
    .card-box { background:#fff; padding:1.1rem 1.4rem; border-radius:10px;
                border:1px solid #e6e8eb; margin-bottom:1rem; }
    .metric-title { color:#5c6a79; font-size:0.78rem; font-weight:600;
                    text-transform:uppercase; letter-spacing:.04em; }
    .metric-value { color:#2c3e50; font-size:1.8rem; font-weight:700; line-height:1.2; }
    .metric-value.bad { color:#DC2626; }
    .metric-sub { color:#9aa6b2; font-size:0.72rem; font-weight:600; }
    .holiday-banner { background:#FFFBEB; border-left:5px solid #F59E0B; padding:.85rem 1rem;
                      color:#92400E; font-weight:600; margin-bottom:1rem; border-radius:6px; }
    .warn-banner { background:#FEF2F2; border-left:5px solid #EF4444; padding:.85rem 1rem;
                   color:#991B1B; font-weight:600; margin-bottom:1rem; border-radius:6px; }
    .ok-banner { background:#ECFDF5; border-left:5px solid #10B981; padding:.6rem 1rem;
                 color:#065F46; font-weight:600; margin-bottom:1rem; border-radius:6px; }
    .app-header { display:flex; align-items:center; gap:1.25rem; background:#fff;
                  border:1px solid #e6e8eb; border-radius:12px; padding:1rem 1.5rem;
                  margin-bottom:1.25rem; }
    .app-header img { height:52px; }
    .app-header .title { font-size:1.6rem; font-weight:800; color:#2c3e50;
                         font-family:system-ui, -apple-system, 'Segoe UI', sans-serif; }
    </style>""",
    unsafe_allow_html=True,
)

init_db()
staff_df = load_staff()
staff_roles = dict(zip(staff_df["name"], staff_df["role"]))
first_aiders = set(staff_df.loc[staff_df["first_aid"] == 1, "name"])
all_shifts = load_shifts()

st.session_state.setdefault("active_date", date.today().isoformat())


def metric_card(col, title, value, ok=True, sub=None):
    cls = "metric-value bad" if not ok else "metric-value"
    sub_html = f'<div class="metric-sub">{sub}</div>' if sub else ""
    col.markdown(
        f'<div class="card-box"><div class="metric-title">{title}</div>'
        f'<div class="{cls}">{value}</div>{sub_html}</div>',
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# SIDEBAR
# --------------------------------------------------------------------------- #
st.sidebar.header("➕ Schedule a shift")
s_role = st.sidebar.selectbox("Filter by position", ROLE_ORDER_HIERARCHY,
                              index=ROLE_ORDER_HIERARCHY.index("Track Marshal"))
staff_for_role = sorted([n for n, r in staff_roles.items() if r == s_role]) or ["Unassigned"]
emp = st.sidebar.selectbox("Employee", staff_for_role)

with st.sidebar.form("shift_form"):
    s_date = st.date_input("Date", value=date.fromisoformat(st.session_state.active_date))
    c1, c2 = st.columns(2)
    s_start = c1.selectbox("Start", TIME_CHOICES, index=safe_index("09:00", TIME_CHOICES))
    s_end = c2.selectbox("End", TIME_CHOICES, index=safe_index("17:00", TIME_CHOICES))
    add_clicked = st.form_submit_button("Add shift", type="primary", use_container_width=True)

if add_clicked:
    d_iso = s_date.strftime("%Y-%m-%d")
    if to_minutes(s_end) <= to_minutes(s_start):
        st.sidebar.error("End time must be after the start time.")
    elif has_conflict(all_shifts, emp, d_iso, s_start, s_end):
        st.sidebar.error(f"{emp} already has an overlapping shift on {d_iso}.")
    else:
        add_shift(emp, staff_roles.get(emp, "Unassigned"), d_iso, s_start, s_end)
        st.rerun()

st.sidebar.write("---")
st.sidebar.header("🔍 Search a person")
search_name = st.sidebar.selectbox("Employee", [""] + sorted(staff_roles.keys()), index=0)


# --------------------------------------------------------------------------- #
# MAIN — branded header
# --------------------------------------------------------------------------- #
st.markdown(
    f'<div class="app-header">'
    f'<img src="data:image/jpeg;base64,{LOGO_B64}" alt="Absolutely Karting"/>'
    f'<div class="title">Maidenhead Rota Tracker</div>'
    f'</div>',
    unsafe_allow_html=True,
)


def update_date():
    st.session_state.active_date = st.session_state.calendar_date.isoformat()


top1, top2 = st.columns([2, 1])
with top1:
    st.date_input("Pick a date", value=date.fromisoformat(st.session_state.active_date),
                  key="calendar_date", on_change=update_date)
with top2:
    view = st.radio("View", ["Day", "Week"], horizontal=True, label_visibility="visible")

active_date = st.session_state.active_date

if (holiday := get_holiday(active_date)):
    st.markdown(f'<div class="holiday-banner">🏫 School holiday: {holiday}</div>', unsafe_allow_html=True)

max_holiday_year = max(int(h["end"][:4]) for h in HOLIDAYS)
if date.today().year > max_holiday_year:
    st.caption(f"⚠ School-holiday dates are set up to {max_holiday_year}. Edit HOLIDAYS in the code to extend them.")


# --------------------------------------------------------------------------- #
# DAY VIEW
# --------------------------------------------------------------------------- #
if view == "Day":
    day_df = all_shifts[all_shifts["Date"] == active_date].copy()

    n_mgmt = int(day_df["Role"].isin(MANAGEMENT_ROLES).sum())
    n_head = int((day_df["Role"] == "Head Marshal").sum())
    n_track = int((day_df["Role"] == "Track Marshal").sum())
    n_fa = int(day_df["Employee"].isin(first_aiders).sum())

    cols = st.columns(5)
    metric_card(cols[0], "Shifts", len(day_df))
    metric_card(cols[1], "Management", n_mgmt, ok=n_mgmt >= MIN_MANAGERS, sub=f"min {MIN_MANAGERS}")
    metric_card(cols[2], "Head Marshals", n_head)
    metric_card(cols[3], "Track Marshals", n_track)
    metric_card(cols[4], "First Aiders", n_fa, ok=n_fa >= MIN_FIRST_AIDERS, sub=f"min {MIN_FIRST_AIDERS}")

    if day_df.empty:
        st.info("No shifts scheduled for this day yet. Add one from the sidebar to get started.")
    else:
        shortfalls = coverage_shortfalls(day_df, first_aiders)
        if shortfalls:
            st.markdown(
                f'<div class="warn-banner">⚠ Staffing shortfall — below minimum on: {", ".join(shortfalls)}.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown('<div class="ok-banner">✓ Minimum coverage met for this day.</div>', unsafe_allow_html=True)

        timeline_html = build_timeline_html(day_df)
        st.markdown(timeline_html, unsafe_allow_html=True)

        st.download_button(
            "⬇ Download this day (CSV)",
            day_df[["Employee", "Role", "Date", "Start", "End"]].to_csv(index=False),
            file_name=f"rota_{active_date}.csv",
            mime="text/csv",
        )

        st.markdown("### ✏️ Edit a shift")
        st.caption("Select a row to change its times or remove it.")
        selection = st.dataframe(
            day_df[["Employee", "Role", "Start", "End"]],
            width="stretch", hide_index=True, height=250,
            selection_mode="single-row", on_select="rerun",
        )
        rows = selection.get("selection", {}).get("rows", [])
        if rows:
            row = day_df.iloc[rows[0]]
            sid = int(row["id"])
            st.write(f"**{row['Employee']}** — {row['Role']}")
            e1, e2 = st.columns(2)
            n_start = e1.selectbox("New start", TIME_CHOICES,
                                   index=safe_index(row["Start"], TIME_CHOICES), key="edit_start")
            n_end = e2.selectbox("New end", TIME_CHOICES,
                                 index=safe_index(row["End"], TIME_CHOICES,
                                                  default=min(safe_index(row["Start"], TIME_CHOICES) + 1, len(TIME_CHOICES) - 1)),
                                 key="edit_end")
            b1, b2 = st.columns(2)
            if b1.button("Apply changes", type="primary", use_container_width=True, key="apply_edit"):
                if to_minutes(n_end) <= to_minutes(n_start):
                    st.error("End time must be after the start time.")
                elif has_conflict(all_shifts, row["Employee"], active_date, n_start, n_end, exclude_id=sid):
                    st.error("That would overlap another shift for this person.")
                else:
                    update_shift(sid, n_start, n_end)
                    st.rerun()
            if b2.button("Delete shift", use_container_width=True, key="delete_edit"):
                delete_shift(sid)
                st.rerun()


# --------------------------------------------------------------------------- #
# WEEK VIEW
# --------------------------------------------------------------------------- #
else:
    sel = date.fromisoformat(active_date)
    monday = sel - timedelta(days=sel.weekday())
    week_days = [(monday + timedelta(days=i)).isoformat() for i in range(7)]
    week_df = all_shifts[all_shifts["Date"].isin(week_days)].copy()

    st.markdown(f"### Week of {monday.strftime('%d %b')} – {(monday + timedelta(days=6)).strftime('%d %b %Y')}")

    if week_df.empty:
        st.info("No shifts scheduled this week. Use the sidebar to add some.")
    else:
        timeline_html = build_timeline_html(week_df)
        st.markdown(timeline_html, unsafe_allow_html=True)

        st.download_button(
            "⬇ Download this week (CSV)",
            week_df[["Employee", "Role", "Date", "Start", "End"]].sort_values(["Date", "Start"]).to_csv(index=False),
            file_name=f"rota_week_{week_days[0]}.csv",
            mime="text/csv",
        )

        left, right = st.columns(2)

        with left:
            st.markdown("#### Hours per person")
            hrs = week_df.copy()
            hrs["Hours"] = [duration_hours(s, e) for s, e in zip(hrs["Start"], hrs["End"])]
            summary = (hrs.groupby(["Employee", "Role"], as_index=False)["Hours"].sum()
                          .sort_values("Hours", ascending=False))
            st.dataframe(summary, width="stretch", hide_index=True)
            st.caption(f"Total scheduled: {summary['Hours'].sum():.1f} hours across {len(summary)} people.")

        with right:
            st.markdown("#### Coverage by day")
            cov_rows = []
            for d in week_days:
                ddf = week_df[week_df["Date"] == d]
                short = coverage_shortfalls(ddf, first_aiders) if not ddf.empty else []
                if ddf.empty:
                    status = "—"
                elif short:
                    status = "⚠ short"
                else:
                    status = "✓ OK"
                cov_rows.append({
                    "Date": pd.to_datetime(d).strftime("%a %d"),
                    "Shifts": len(ddf),
                    "Mgmt": int(ddf["Role"].isin(MANAGEMENT_ROLES).sum()),
                    "First aid": int(ddf["Employee"].isin(first_aiders).sum()),
                    "Track": int((ddf["Role"] == "Track Marshal").sum()),
                    "Status": status,
                })
            st.dataframe(pd.DataFrame(cov_rows), width="stretch", hide_index=True)


# --------------------------------------------------------------------------- #
# SEARCH RESULTS
# --------------------------------------------------------------------------- #
if search_name:
    st.markdown("---")
    st.markdown(f"### 📋 Shifts for {search_name}")
    res = all_shifts[all_shifts["Employee"] == search_name].sort_values("Date").copy()
    if res.empty:
        st.warning("No shifts found for this person.")
    else:
        res["Hours"] = [duration_hours(s, e) for s, e in zip(res["Start"], res["End"])]
        st.caption(f"{len(res)} shifts · {res['Hours'].sum():.1f} hours total")
        st.dataframe(res[["Date", "Role", "Start", "End", "Hours"]], width="stretch", hide_index=True)


# --------------------------------------------------------------------------- #
# ADD OR UPDATE STAFF TO DATABASE (collapsed)
# --------------------------------------------------------------------------- #
st.markdown("---")
with st.expander("👤 Add or update staff to database"):
    with st.form("staff_form", clear_on_submit=True):
        new_name = st.text_input("Full name")
        new_role = st.selectbox("Role", ROLE_ORDER_HIERARCHY[:-1])
        new_fa = st.checkbox("First-aid trained")
        staff_clicked = st.form_submit_button("Save staff member", type="primary")

    if staff_clicked:
        if new_name.strip():
            upsert_staff(new_name.strip(), new_role, new_fa)
            st.success(f"Saved {new_name.strip()}.")
            st.rerun()
        else:
            st.warning("Enter a name first.")


# --------------------------------------------------------------------------- #
# DATABASE MANAGEMENT (collapsed)
# --------------------------------------------------------------------------- #
with st.expander("🗑️ Database management — bulk edit all shifts"):
    st.caption("Edit any cell, add rows, or delete rows, then save. Role is set automatically "
               "from the staff list. Rows where the end time is not after the start are skipped.")
    bulk = all_shifts[["Employee", "Role", "Date", "Start", "End"]].copy()
    bulk["Date"] = pd.to_datetime(bulk["Date"], errors="coerce").dt.date

    emp_opts = sorted(set(staff_roles.keys()) | set(bulk["Employee"].dropna()))
    extra_times = sorted((set(bulk["Start"].dropna()) | set(bulk["End"].dropna())) - set(TIME_CHOICES))
    time_opts = TIME_CHOICES + extra_times

    edited = st.data_editor(
        bulk,
        num_rows="dynamic",
        width="stretch",
        key="bulk_editor",
        column_config={
            "Employee": st.column_config.SelectboxColumn("Employee", options=emp_opts, required=True),
            "Role": st.column_config.TextColumn("Role (auto)", disabled=True),
            "Date": st.column_config.DateColumn("Date", format="YYYY-MM-DD", required=True),
            "Start": st.column_config.SelectboxColumn("Start", options=time_opts, required=True),
            "End": st.column_config.SelectboxColumn("End", options=time_opts, required=True),
        },
    )

    if st.button("Save all changes", type="primary"):
        valid, skipped = [], 0
        for _, r in edited.iterrows():
            empv, datev, sv, ev = r["Employee"], r["Date"], r["Start"], r["End"]
            if pd.isna(empv) or pd.isna(datev) or pd.isna(sv) or pd.isna(ev):
                skipped += 1
                continue
            d_iso = pd.to_datetime(datev).strftime("%Y-%m-%d")
            if to_minutes(str(ev)) <= to_minutes(str(sv)):
                skipped += 1
                continue
            valid.append((str(empv), staff_roles.get(empv, "Unassigned"), d_iso, str(sv), str(ev)))
        replace_all_shifts(valid)
        msg = f"Saved {len(valid)} shifts."
        if skipped:
            msg += f" Skipped {skipped} incomplete or invalid row(s)."
        st.success(msg)
        st.rerun()
