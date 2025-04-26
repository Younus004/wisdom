# auth.py
import streamlit as st

def require_front_office():
    if "id_token" not in st.session_state:
        st.error("🔐 Please log in first.")
        st.stop()
    if st.session_state.get("role") != "Front Office":
        st.error("⛔ Access denied for your role.")
        st.stop()
