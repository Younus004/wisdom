import streamlit as st

if "id_token" not in st.session_state:
    st.error("Please log in first.")
    st.stop()
if st.session_state.get("role") != "Front Office":
    st.error("Access denied: Front Office only.")
    st.stop()

import os
import streamlit as st
import pandas as pd
from datetime import datetime, date, time, timedelta
import firebase_admin
from firebase_admin import credentials, firestore

# ─── Page config & Firebase init ────────────────────────────────────────────────
st.set_page_config(page_title="Visitor Log", layout="wide")
if not firebase_admin._apps:
    cred = credentials.Certificate("D:/wisdom/wisdom-schools-firebase-adminsdk-fbsvc-971bbaec20.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

# ─── Header ───────────────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='text-align:center; color:#2E86C1;'>📅 Visitor Log</h1>",
    unsafe_allow_html=True
)
st.write("")  # spacer

# ─── Add New Visitor ──────────────────────────────────────────────────────────────
with st.expander("➕ Log New Visitor", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        name    = st.text_input("Visitor Name")
        mobile  = st.text_input("Mobile Number")
        purpose = st.selectbox("Purpose", [
            "General Visit",
            "Collect Child",
            "Repair",
            "Meet Teacher/Staff",
            "Meet Principal"
        ])
    with col2:
        child = ""
        if purpose == "Collect Child":
            students = [
                s.to_dict().get("name","") + f" ({s.to_dict().get('admission_no','')})"
                for s in db.collection("students").stream()
            ]
            child = st.selectbox("Select Child", [""] + sorted(filter(None, students)))
        details = st.text_area("Additional Details")
    if st.button("✅ Log Visitor"):
        if not name or not mobile:
            st.error("Name & mobile are required.")
        else:
            rec = {
                "name":     name.strip(),
                "mobile":   mobile.strip(),
                "purpose":  purpose,
                "child":    child if purpose=="Collect Child" else "",
                "details":  details.strip(),
                "time_in":  datetime.now().isoformat(),
                "time_out": None
            }
            try:
                db.collection("visitors").add(rec)
                st.success("Visitor logged successfully!")
            except Exception as e:
                st.error(f"Error logging visitor: {e}")

st.markdown("---")

# ─── Date picker to view logs ────────────────────────────────────────────────────
view_date = st.date_input("📅 Select Date", value=date.today())
start   = datetime.combine(view_date, time.min)
end     = start + timedelta(days=1)

# ─── Fetch & Normalize ────────────────────────────────────────────────────────────
def _to_dt(val):
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val)
        except:
            return None
    return None

docs = (
    db.collection("visitors")
      .where("time_in", ">=", start)
      .where("time_in", "<",  end)
      .stream()
)

rows = []
for d in docs:
    v     = d.to_dict()
    tin   = _to_dt(v.get("time_in"))
    tout  = _to_dt(v.get("time_out"))
    if not tin:
        continue
    rows.append({
        "id":       d.id,
        "Name":     v.get("name","—"),
        "Mobile":   v.get("mobile","—"),
        "Purpose":  v.get("purpose","—"),
        "Child":    v.get("child","—"),
        "Time In":  tin.strftime("%I:%M %p"),
        "Time Out": tout.strftime("%I:%M %p") if tout else "—",
        "Details":  v.get("details","—")
    })

df = pd.DataFrame(rows)

# ─── Filters & Search ─────────────────────────────────────────────────────────────
colA, colB = st.columns((3,1))
with colA:
    query = st.text_input("🔍 Search Name / Mobile / Purpose")
with colB:
    purpose_filter = st.selectbox(
        "Purpose Filter",
        ["All"] + sorted(df["Purpose"].unique())
    )

if purpose_filter != "All":
    df = df[df["Purpose"] == purpose_filter]

if query:
    q = query.lower()
    df = df[df.apply(
        lambda r: q in str(r["Name"]).lower()
              or q in str(r["Mobile"])
              or q in str(r["Purpose"]).lower(),
        axis=1
    )]

# ─── Display Table with Time-Out Buttons ──────────────────────────────────────────
st.markdown("### 👥 Visitors on " + view_date.strftime("%d %b %Y"))
if df.empty:
    st.info("No visitors logged for this date.")
else:
    # header row
    cols = st.columns([2,1,1,1,1,1,2,1])
    for c, h in zip(cols, ["Name","Mobile","Purpose","Child","Time In","Time Out","Details","Action"]):
        c.markdown(f"**{h}**")
    # data rows
    for _, row in df.iterrows():
        cols = st.columns([2,1,1,1,1,1,2,1])
        cols[0].write(row["Name"])
        cols[1].write(row["Mobile"])
        cols[2].write(row["Purpose"])
        cols[3].write(row["Child"])
        cols[4].write(row["Time In"])
        cols[5].write(row["Time Out"])
        cols[6].write(row["Details"])
        # only show button if time_out missing
        if row["Time Out"] == "—":
            if cols[7].button("🕓 Mark Time-Out", key=row["id"]):
                try:
                    db.collection("visitors").document(row["id"]).update({
                        "time_out": datetime.now().isoformat()
                    })
                    st.success(f"Time-out recorded for {row['Name']}")
                    # re-run so the new Time-Out shows up
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Failed to set time-out: {e}")
        else:
            cols[7].write("✅ Done")
