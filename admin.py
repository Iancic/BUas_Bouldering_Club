import streamlit as st
import sqlite3
import pandas as pd
import os
from pathlib import Path

# ——————————————————————————————————————————————————————————
# Admin interface for app.db
# ——————————————————————————————————————————————————————————
st.set_page_config(
    page_title="Admin – Climbing Gym DB",
    layout="wide"
)

st.title("Database Administration")

# Determine path to app.db relative to this script
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / 'app.db'

# Connect to SQLite database
conn = sqlite3.connect(DB_PATH, check_same_thread=False)

# Function to load and filter table into DataFrame
def load_and_filter_table(name, search_term):
    df = pd.read_sql(f"SELECT * FROM {name}", conn)
    if search_term:
        mask = df.apply(
            lambda row: row.astype(str)
                          .str.contains(search_term, case=False, na=False)
                          .any(),
            axis=1
        )
        df = df[mask]
    return df

# --- Registrations Table ---
st.header("Registrations")
search_regs = st.text_input("Search Registrations", key="search_regs")
df_regs = load_and_filter_table('registrations', search_regs)
edited_regs = st.data_editor(
    df_regs,
    num_rows="dynamic",
    key="regs_editor",
    use_container_width=True
)
if st.button("Save Registrations Changes"):
    conn.execute('DELETE FROM registrations')
    conn.commit()
    edited_regs.to_sql('registrations', conn, if_exists='append', index=False)
    st.success("Registrations table updated.")

st.markdown("---")

# --- Winners Table ---
st.header("Winners")
search_wins = st.text_input("Search Winners", key="search_wins")
df_wins = load_and_filter_table('winners', search_wins)
edited_wins = st.data_editor(
    df_wins,
    num_rows="dynamic",
    key="wins_editor",
    use_container_width=True
)
if st.button("Save Winners Changes"):
    conn.execute('DELETE FROM winners')
    conn.commit()
    edited_wins.to_sql('winners', conn, if_exists='append', index=False)
    st.success("Winners table updated.")

st.markdown("---")

st.info("Use the search boxes above to filter table contents. Edit cells directly and click 'Save' to apply changes.")
