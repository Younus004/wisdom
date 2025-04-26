
import streamlit as st

# Sidebar Navigation
st.set_page_config(page_title="Wisdom Schools - Front Office", layout="wide")
st.image("wisdom logo.png", width=120)
st.title("🏫 Wisdom Schools - Front Office Dashboard")

menu = st.sidebar.selectbox(
    "📁 Menu",
    ["🏠 Dashboard", "📝 Register Student", "💳 Fee Collection", "📋 Registered Students", "🧾 Visitors List", "📨 Enquiry Form (Coming Soon)"]
)

if menu == "🏠 Dashboard":
    st.subheader("📊 Welcome to Front Office Dashboard")
    st.markdown("Use the left menu to navigate to different sections.")

elif menu == "📝 Register Student":
    st.subheader("📝 Student Registration")
    st.markdown("This will load the latest student registration form.")
    with open("wisdom_register_student_ordered_layout.py", "r", encoding="utf-8") as f:
        exec(f.read())

elif menu == "💳 Fee Collection":
    st.subheader("💳 Fee Collection")
    st.markdown("📌 List of students with pending fee, reminder log, and payment update coming soon.")

elif menu == "📋 Registered Students":
    st.subheader("📋 View Registered Students")
    st.markdown("📥 You will be able to download registration forms and fee receipts from here (in progress).")

elif menu == "🧾 Visitors List":
    st.subheader("🧾 Visitors List")
    st.markdown("Visitor tracking will be added here.")

elif menu == "📨 Enquiry Form (Coming Soon)":
    st.subheader("📨 Enquiry Management")
    st.info("🔧 This module is under construction.")
