"""
Maidenhead Rota & School Holiday Tracker
----------------------------------------
A Streamlit rota for a karting centre. Data lives in a local SQLite file
(rota.db) so several people can use it without overwriting each other, and
day-to-day adds/edits/deletes are written one row at a time.

Run with:  streamlit run app.py
On first launch any existing rota_database.csv is imported automatically.
"""

import os
import sqlite3
from datetime import date, datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

# --------------------------------------------------------------------------- #
# CONFIGURATION
# --------------------------------------------------------------------------- #
DB_PATH = "rota.db"
LEGACY_CSV = "rota_database.csv"  # auto-imported once if present

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

# A palette where the three management blues no longer blur together.
ROLE_COLORS = {
    "Centre Manager": "#1F3A5F",     # navy
    "Assistant Manager": "#6C5CE7",  # violet
    "Duty Manager": "#16A085",       # teal
    "Head Marshal": "#2980B9",       # blue
    "Mechanic": "#C0392B",           # red
    "Track Marshal": "#E67E22",      # orange
    "Unassigned": "#95A5A6",         # grey
}

# Minimum coverage per scheduled day. Edit to match your operating policy.
MIN_FIRST_AIDERS = 1
MIN_MANAGERS = 1
MIN_TRACK_MARSHALS = 2

# Operating hours used to frame the day timeline.
OPEN_TIME = "08:00"
CLOSE_TIME = "22:00"

TIME_CHOICES = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]
FONT_STACK = "system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"

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
    """Create tables, seed staff, and migrate the legacy CSV once."""
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
                pass  # a malformed legacy file should never block start-up
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
    """Bulk admin save: rewrite the shifts table from a validated set of rows."""
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
    n_track = (day_df["Role"] == "Track Marshal").sum()
    out = []
    if n_fa < MIN_FIRST_AIDERS:
        out.append(f"first aiders ({n_fa}/{MIN_FIRST_AIDERS})")
    if n_mgmt < MIN_MANAGERS:
        out.append(f"management ({n_mgmt}/{MIN_MANAGERS})")
    if n_track < MIN_TRACK_MARSHALS:
        out.append(f"track marshals ({n_track}/{MIN_TRACK_MARSHALS})")
    return out


def get_holiday(d):
    for h in HOLIDAYS:
        if h["start"] <= d <= h["end"]:
            return h["name"]
    return None


def build_timeline(df, x_start_dt, x_end_dt, height, day_ticks=False):
    plot_df = df.copy()
    plot_df["Hours"] = [duration_hours(s, e) for s, e in zip(plot_df["Start"], plot_df["End"])]
    plot_df["BarStart"] = pd.to_datetime(plot_df["Date"] + " " + plot_df["Start"])
    plot_df["BarEnd"] = pd.to_datetime(plot_df["Date"] + " " + plot_df["End"])
    fig = px.timeline(
        plot_df,
        x_start="BarStart",
        x_end="BarEnd",
        y="Employee",
        color="Role",
        color_discrete_map=ROLE_COLORS,
        category_orders={"Role": ROLE_ORDER_HIERARCHY},
        hover_data={"Hours": True, "Start": True, "End": True,
                    "BarStart": False, "BarEnd": False, "Employee": False},
    )
    fig.update_yaxes(autorange="reversed", title=None)
    fig.update_xaxes(range=[x_start_dt, x_end_dt], title=None,
                     gridcolor="#EDF1F5", showgrid=True)
    if day_ticks:
        fig.update_xaxes(dtick=86400000.0, tickformat="%a %d %b")
    fig.update_layout(
        template="plotly_white",
        font=dict(family=FONT_STACK, size=13, color="#2c3e50"),
        height=height,
        margin=dict(l=8, r=8, t=8, b=8),
        legend_title_text="Role",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        bargap=0.25,
    )
    return fig


# --------------------------------------------------------------------------- #
# PAGE SETUP
# --------------------------------------------------------------------------- #
st.set_page_config(layout="wide", page_title="Maidenhead Rota", page_icon="🏎️")
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
# SIDEBAR — schedule, add staff, search
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
st.sidebar.header("👤 Add or update staff")
with st.sidebar.form("staff_form", clear_on_submit=True):
    new_name = st.text_input("Full name")
    new_role = st.selectbox("Role", ROLE_ORDER_HIERARCHY[:-1])  # excludes "Unassigned"
    new_fa = st.checkbox("First-aid trained")
    staff_clicked = st.form_submit_button("Save staff member", use_container_width=True)

if staff_clicked:
    if new_name.strip():
        upsert_staff(new_name.strip(), new_role, new_fa)
        st.rerun()
    else:
        st.sidebar.warning("Enter a name first.")

st.sidebar.write("---")
st.sidebar.header("🔍 Search a person")
search_name = st.sidebar.selectbox("Employee", [""] + sorted(staff_roles.keys()), index=0)


# --------------------------------------------------------------------------- #
# MAIN — header, date picker, view toggle
# --------------------------------------------------------------------------- #
st.title("🏎️ Maidenhead Rota & School Holiday Tracker")


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
    metric_card(cols[3], "Track Marshals", n_track, ok=n_track >= MIN_TRACK_MARSHALS, sub=f"min {MIN_TRACK_MARSHALS}")
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

        x0 = pd.to_datetime(f"{active_date} {OPEN_TIME}")
        x1 = pd.to_datetime(f"{active_date} {CLOSE_TIME}")
        height = max(240, 42 * day_df["Employee"].nunique() + 90)
        st.plotly_chart(build_timeline(day_df, x0, x1, height), use_container_width=True)

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
        x0 = pd.to_datetime(f"{week_days[0]} 00:00")
        x1 = pd.to_datetime(f"{week_days[6]} 00:00") + timedelta(days=1)
        height = max(280, 40 * week_df["Employee"].nunique() + 110)
        st.plotly_chart(build_timeline(week_df, x0, x1, height, day_ticks=True), use_container_width=True)

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
# SEARCH RESULTS (shown in both views)
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
# DATABASE MANAGEMENT (bulk edit, persists on save)
# --------------------------------------------------------------------------- #
st.markdown("---")
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
