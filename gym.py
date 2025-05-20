# Full fixed code for app.py with Admin input in sidebar for visibility
import streamlit as st
import sqlite3
import datetime
import random
import pytz

# ——————————————————————————————————————————————————————————
# Configuration
# ——————————————————————————————————————————————————————————
st.set_page_config(
    page_title="Climbing Gym – Weekly Management",
    layout="centered"
)

# ——————————————————————————————————————————————————————————
# Admin Settings
# ——————————————————————————————————————————————————————————
# Define your admin keyword here (in production, use secure storage)
ADMIN_KEYWORD = "letmein"  # Change to your secret phrase

# ——————————————————————————————————————————————————————————
# Database connection
# ——————————————————————————————————————————————————————————
conn = sqlite3.connect('app.db', check_same_thread=False)
cursor = conn.cursor()
# Initialize tables if not exist
cursor.execute(
    '''
    CREATE TABLE IF NOT EXISTS registrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        phone TEXT NOT NULL DEFAULT '',
        timestamp INTEGER NOT NULL,
        draw_time INTEGER NOT NULL,
        UNIQUE(student_id, draw_time)
    )
    '''
)
cursor.execute(
    '''
    CREATE TABLE IF NOT EXISTS winners (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        draw_time INTEGER NOT NULL,
        category TEXT NOT NULL CHECK(category in ('winner','reserve'))
    )
    '''
)
conn.commit()

# ——————————————————————————————————————————————————————————
# Time utilities
# ——————————————————————————————————————————————————————————
tz = pytz.timezone('Europe/Bucharest')
def now_dt():
    return datetime.datetime.now(tz)

def compute_draw_times(current):
    week_start = current - datetime.timedelta(days=current.weekday())
    monday_draw = week_start.replace(hour=5, minute=0, second=0, microsecond=0)
    if current < monday_draw:
        return monday_draw - datetime.timedelta(weeks=1), monday_draw
    return monday_draw, monday_draw + datetime.timedelta(weeks=1)

# ——————————————————————————————————————————————————————————
# Draw logic
# ——————————————————————————————————————————————————————————
def perform_weekly_draw():
    now = now_dt()
    current_draw, _ = compute_draw_times(now)
    ts = int(current_draw.timestamp())
    cursor.execute('SELECT COUNT(*) FROM registrations WHERE draw_time=?', (ts,))
    if cursor.fetchone()[0] and now >= current_draw:
        cursor.execute('SELECT COUNT(*) FROM winners WHERE draw_time=?', (ts,))
        if cursor.fetchone()[0] == 0:
            cursor.execute('SELECT student_id, first_name, last_name, phone FROM registrations WHERE draw_time=?', (ts,))
            rows = cursor.fetchall()
            winners = random.sample(rows, min(15, len(rows)))
            reserves = random.sample([r for r in rows if r not in winners], min(10, len(rows) - len(winners)))
            for sid, fn, ln, ph in winners:
                cursor.execute('INSERT INTO winners(student_id, first_name, last_name, draw_time, category) VALUES (?, ?, ?, ?, ?)',
                               (sid, fn, ln, ts, 'winner'))
            for sid, fn, ln, ph in reserves:
                cursor.execute('INSERT INTO winners(student_id, first_name, last_name, draw_time, category) VALUES (?, ?, ?, ?, ?)',
                               (sid, fn, ln, ts, 'reserve'))
            cursor.execute('DELETE FROM registrations WHERE draw_time=?', (ts,))
            conn.commit()
perform_weekly_draw()

# ——————————————————————————————————————————————————————————
# UI: Header + Sidebar Admin Login
# ——————————————————————————————————————————————————————————
st.title("Climbing Gym – Weekly Management")

# Sidebar: Admin Login for better visibility
dashboard = st.sidebar
admin_input = dashboard.text_input("Admin Keyword (leave blank for user view)", type="password")
is_admin = (admin_input.strip() == ADMIN_KEYWORD)
if is_admin:
    dashboard.success("Admin mode activated")

# ——————————————————————————————————————————————————————————
# UI: Current Week Winners
# ——————————————————————————————————————————————————————————
now = now_dt()
current_draw, next_draw = compute_draw_times(now)
 ts_current = int(current_draw.timestamp())

st.header("Current Week Winners")
col1, col2 = st.columns(2)
with col1:
    st.subheader("Free Access (15 spots)")
    cursor.execute('SELECT student_id, first_name, last_name FROM winners WHERE draw_time=? AND category="winner"',
                   (ts_current,))
    for sid, fn, ln in cursor.fetchall():
        st.write(f"{sid} – {fn} {ln}")
with col2:
    st.subheader("Reserve List (10 spots)")
    cursor.execute('SELECT student_id, first_name, last_name FROM winners WHERE draw_time=? AND category="reserve"',
                   (ts_current,))
    for sid, fn, ln in cursor.fetchall():
        st.write(f"{sid} – {fn} {ln}")
st.markdown("---")

# ——————————————————————————————————————————————————————————
# UI: Registration Section
# ——————————————————————————————————————————————————————————
start, end = next_draw.date(), (next_draw + datetime.timedelta(days=6)).date()
st.header(f"Registration for Week {start.strftime('%d.%m')} – {end.strftime('%d.%m')}")

remaining = next_draw - now
days, rem = remaining.days, remaining.seconds
hours = rem // 3600
minutes = (rem % 3600) // 60
st.subheader("Time Until Draw")
st.markdown(f"<h2 style='background-color:#4CAF50; color:white; padding:10px; text-align:center; border-radius:5px;'>{days}d {hours}h {minutes}m</h2>", unsafe_allow_html=True)

# ——————————————————————————————————————————————————————————
# UI: Registration Form
# ——————————————————————————————————————————————————————————
with st.form("registration_form"):
    sid = st.text_input("Student ID")
    fname = st.text_input("First Name")
    lname = st.text_input("Last Name")
    phone = st.text_input("Phone Number")
    submitted = st.form_submit_button("Register")
    if submitted:
        if not (sid.strip() and fname.strip() and lname.strip() and phone.strip()):
            st.error("All fields are required.")
        else:
            ts_next = int(next_draw.timestamp())
            cursor.execute('SELECT COUNT(*) FROM registrations WHERE draw_time=? AND student_id=?', (ts_next, sid.strip()))
            if cursor.fetchone()[0]:
                st.warning("This Student ID is already registered for next week.")
            else:
                cursor.execute('INSERT INTO registrations(student_id, first_name, last_name, phone, timestamp, draw_time) VALUES (?, ?, ?, ?, ?, ?)',
                               (sid.strip(), fname.strip(), lname.strip(), phone.strip(), int(now.timestamp()), ts_next))
                conn.commit()
                st.success("Registration successful!")

# ——————————————————————————————————————————————————————————
# UI: Registered Students List
# ——————————————————————————————————————————————————————————
ts_next = int(next_draw.timestamp())
cursor.execute('SELECT id, student_id, first_name, last_name, phone, timestamp FROM registrations WHERE draw_time=? ORDER BY timestamp DESC', (ts_next,))
regs = cursor.fetchall()
st.subheader(f"{len(regs)} Registered for Next Week")

# Admin: removal controls
if is_admin and regs:
    st.markdown("**Admin Controls: Remove Registrations**")
    to_remove = st.multiselect("Select registrations to remove:",
                               options=[f"{r[0]}: {r[1]} – {r[2]} {r[3]}" for r in regs])
    if st.button("Remove Selected"):
        removed_ids = [int(item.split(":")[0]) for item in to_remove]
        cursor.executemany('DELETE FROM registrations WHERE id=?', [(rid,) for rid in removed_ids])
        conn.commit()
        st.success(f"Removed {len(removed_ids)} registration(s).")
        st.experimental_rerun()

# Display list
for rid, sid, fn, ln, ph, ts in regs:
    dt = datetime.datetime.fromtimestamp(ts, tz)
    weekday = dt.strftime('%A')
    st.write(f"{sid} – {fn} {ln} – {ph} – {weekday}, {dt.strftime('%d/%m/%Y %H:%M')}")
