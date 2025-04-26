# File: home.py

import streamlit as st
import importlib
from datetime import datetime
import pytz

# ─── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="🏫 Wisdom Schools Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── LOGIN SCREEN ────────────────────────────────────────────────────────────────
def show_login():
    st.title("🔐 Front Office Login")
    user = st.text_input("Login ID")
    pwd  = st.text_input("Password", type="password")
    if st.button("Log in"):
        if user == "frontoffice" and pwd == "admi123":
            st.session_state.id_token = "dummy-token"
            st.session_state.role     = "Front Office"
            st.experimental_rerun()
        else:
            st.error("Invalid credentials")

if "id_token" not in st.session_state:
    show_login()
    st.stop()

if st.session_state.get("role") != "Front Office":
    st.error("⛔ Access denied: Front Office only.")
    st.stop()

# ─── SIDEBAR ────────────────────────────────────────────────────────────────────
st.sidebar.markdown(
    """
    <div style="text-align:center; margin-bottom:1rem;">
      <h2 style="color:#004466;">🎓 Wisdom Schools</h2>
    </div>
    """, unsafe_allow_html=True
)

# Live date & time
india_tz = pytz.timezone("Asia/Kolkata")
now = datetime.now(india_tz)
st.sidebar.markdown(
    f"### 🗓️ {now.strftime('%A, %d %B %Y')}  \n" +
    f"### ⏰ {now.strftime('%I:%M:%S %p')}"
)

st.sidebar.markdown("---")

# Navigation menu
pages = {
    "1️⃣ Register Student":    "register_student",
    "2️⃣ Registered Students": "registered_students",
    "3️⃣ Fee Collection":      "fee_collection",
    "4️⃣ Enquiries":           "manage_enquiries",
    "5️⃣ Visitors":            "manage_visitors",
}
choice = st.sidebar.radio("Navigate to", list(pages.keys()), index=0)

# ─── PAGE ROUTING ────────────────────────────────────────────────────────────────
module_name = pages[choice]
try:
    page = importlib.import_module(f"pages.{module_name}")
    page.main()
except ModuleNotFoundError:
    st.error(f"🛑 Module pages/{module_name}.py not found.")
