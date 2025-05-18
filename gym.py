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
# Database connection (single connection)
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
        phone TEXT NOT NULL,
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

# Compute draw datetimes for Monday 05:00
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
    reg_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM winners WHERE draw_time=?', (ts,))
    win_count = cursor.fetchone()[0]
    if now >= current_draw and reg_count > 0 and win_count == 0:
        cursor.execute('SELECT student_id, first_name, last_name, phone FROM registrations WHERE draw_time=?', (ts,))
        rows = cursor.fetchall()
        winners = random.sample(rows, min(15, len(rows)))
        reserves = random.sample([r for r in rows if r not in winners], min(10, len(rows) - len(winners)))
        for sid, fn, ln, ph in winners:
            cursor.execute(
                'INSERT INTO winners(student_id, first_name, last_name, draw_time, category) VALUES (?, ?, ?, ?, ?)',
                (sid, fn, ln, ts, 'winner')
            )
        for sid, fn, ln, ph in reserves:
            cursor.execute(
                'INSERT INTO winners(student_id, first_name, last_name, draw_time, category) VALUES (?, ?, ?, ?, ?)',
                (sid, fn, ln, ts, 'reserve')
            )
        cursor.execute('DELETE FROM registrations WHERE draw_time=?', (ts,))
        conn.commit()

perform_weekly_draw()

# ——————————————————————————————————————————————————————————
# UI: Header
# ——————————————————————————————————————————————————————————
st.title("Climbing Gym – Weekly Management")

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
    cursor.execute(
        'SELECT student_id, first_name, last_name FROM winners WHERE draw_time=? AND category="winner"',
        (ts_current,)
    )
    for sid, fn, ln in cursor.fetchall():
        st.write(f"{sid} – {fn} {ln}")
with col2:
    st.subheader("Reserve List (10 spots)")
    cursor.execute(
        'SELECT student_id, first_name, last_name FROM winners WHERE draw_time=? AND category="reserve"',
        (ts_current,)
    )
    for sid, fn, ln in cursor.fetchall():
        st.write(f"{sid} – {fn} {ln}")

st.markdown("---")

# ——————————————————————————————————————————————————————————
# UI: Registration Section
# ——————————————————————————————————————————————————————————
start, end = next_draw.date(), (next_draw + datetime.timedelta(days=6)).date()
st.header(f"Registration for Week {start.strftime('%d.%m')} – {end.strftime('%d.%m')}")

# Countdown
remaining = next_draw - now
days, rem = remaining.days, remaining.seconds
hours = rem // 3600
minutes = (rem % 3600) // 60
st.subheader("Time Until Draw")
st.markdown(
    f"<h2 style='background-color:#4CAF50; color:white; padding:10px; text-align:center; border-radius:5px;'>{days}d {hours}h {minutes}m</h2>",
    unsafe_allow_html=True
)

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
        # Validate all fields
        if not sid.strip() or not fname.strip() or not lname.strip() or not phone.strip():
            st.error("All fields are required. Please fill in Student ID, First Name, Last Name, and Phone Number.")
        else:
            ts_next = int(next_draw.timestamp())
            cursor.execute(
                'SELECT COUNT(*) FROM registrations WHERE draw_time=? AND student_id=?',
                (ts_next, sid.strip())
            )
            if cursor.fetchone()[0]:
                st.warning("This Student ID is already registered for next week.")
            else:
                cursor.execute(
                    'INSERT INTO registrations(student_id, first_name, last_name, phone, timestamp, draw_time) VALUES (?, ?, ?, ?, ?, ?)',
                    (sid.strip(), fname.strip(), lname.strip(), phone.strip(), int(now.timestamp()), ts_next)
                )
                conn.commit()
                st.success("Registration successful!")

# ——————————————————————————————————————————————————————————
# UI: Populate Dummy Winners (Testing)
# ——————————————————————————————————————————————————————————
if st.button("Populate Dummy Winners"):
    cursor.execute('DELETE FROM winners WHERE draw_time=?', (ts_current,))
    dummy_free = [("TEST01","Alice","Smith"),("TEST02","Bob","Brown"),("TEST03","Carol","Johnson")]
    for sid_f, fn_f, ln_f in dummy_free:
        cursor.execute(
            'INSERT INTO winners(student_id, first_name, last_name, draw_time, category) VALUES (?,?,?,?,?)',
            (sid_f, fn_f, ln_f, ts_current, 'winner')
        )
    dummy_reserve = [("TEST11","Dave","Lee"),("TEST12","Eve","White")]
    for sid_r, fn_r, ln_r in dummy_reserve:
        cursor.execute(
            'INSERT INTO winners(student_id, first_name, last_name, draw_time, category) VALUES (?,?,?,?,?)',
            (sid_r, fn_r, ln_r, ts_current, 'reserve')
        )
    conn.commit()
    st.success("Dummy winners populated.")

# ——————————————————————————————————————————————————————————
# UI: Registered Students List
# ——————————————————————————————————————————————————————————
ts_next = int(next_draw.timestamp())
cursor.execute(
    'SELECT student_id, first_name, last_name, phone, timestamp FROM registrations WHERE draw_time=? ORDER BY timestamp DESC',
    (ts_next,)
)
regs = cursor.fetchall()
st.subheader(f"{len(regs)} Registered for Next Week")
for sid, fn, ln, ph, ts in regs:
    dt = datetime.datetime.fromtimestamp(ts, tz)
    weekday = dt.strftime('%A')
    st.write(f"{sid} – {fn} {ln} – {ph} – {weekday}, {dt.strftime('%d/%m/%Y %H:%M')}")

# ——————————————————————————————————————————————————————————
# UI: Clear Registrations
# ——————————————————————————————————————————————————————————
if st.button("Delete All Registrations for Next Week"):
    cursor.execute('DELETE FROM registrations WHERE draw_time=?', (ts_next,))
    conn.commit()
    st.success("All registrations for next week have been deleted.")