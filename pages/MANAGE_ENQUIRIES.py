import streamlit as st

if "id_token" not in st.session_state:
    st.error("Please log in first.")
    st.stop()
if st.session_state.get("role") != "Front Office":
    st.error("Access denied: Front Office only.")
    st.stop()


# Now your existing page code can run…

# File: pages/6_enquiry_section.py

import re
from datetime import date, datetime
import pandas as pd
import streamlit as st

import firebase_admin
from firebase_admin import credentials, firestore

# ─── Firebase Init ───────────────────────────────────────────────────────────────
if not firebase_admin._apps:
    cred = credentials.Certificate("D:/wisdom/wisdom-schools-firebase-adminsdk-fbsvc-971bbaec20.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

# ─── Helpers ─────────────────────────────────────────────────────────────────────
def fetch_enquiries():
    docs = (
        db.collection("enquiries")
          .order_by("inquiry_date", direction=firestore.Query.DESCENDING)
          .stream()
    )
    rows = []
    for d in docs:
        e = d.to_dict()
        e["id"] = d.id
        # count follow‑ups
        fus = db.collection("enquiries").document(d.id).collection("followups").stream()
        e["follow_up_count"] = sum(1 for _ in fus)
        rows.append(e)
    return pd.DataFrame(rows)

def add_followup(enq_id: str, comment: str, next_dt: datetime):
    # write new follow‑up record
    db.collection("enquiries") \
      .document(enq_id) \
      .collection("followups") \
      .add({
          "comment": comment,
          "timestamp": datetime.now().isoformat(),
          "next_followup": next_dt.isoformat()
      })
    # update parent doc’s next_followup
    db.collection("enquiries").document(enq_id).update({
        "next_followup": next_dt.isoformat()
    })


# ─── Page Setup ─────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Enquiries", layout="wide")
st.title("📝 Manage Enquiries")


# ─── Add New Enquiry ─────────────────────────────────────────────────────────────
with st.expander("➕ Add New Enquiry", expanded=True):
    with st.form("add_enquiry", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            name   = st.text_input("Name *")
            mobile = st.text_input("Mobile * (10 digits)", max_chars=10)
            email  = st.text_input("Email")
        with c2:
            cls    = st.selectbox(
                "Class Interested *",
                ["","Nursery","LKG","UKG"] + [str(i) for i in range(1,11)]
            )
            source = st.selectbox("Source", ["","Website","Walk‑in","Referral","Ad","Other"])
            status = st.selectbox("Status", ["New","Contacted","Converted","Not Interested"])
        with c3:
            lead_temp    = st.selectbox("Lead Temperature *", ["Hot","Warm","Cold"])
            notes        = st.text_area("Initial Notes")
            inq_date     = st.date_input("Inquiry Date", date.today())
            next_fu_date = st.date_input("Next Follow‑Up Date", date.today())
            next_fu_time = st.time_input("Next Follow‑Up Time", datetime.now().time())

        submitted = st.form_submit_button("Save Enquiry")
        if submitted:
            # basic validation
            if not (name and re.fullmatch(r"\d{10}", mobile) and cls and lead_temp):
                st.error("Please fill Name, 10‑digit Mobile, Class & Lead Temp.")
            else:
                next_dt = datetime.combine(next_fu_date, next_fu_time)
                doc = {
                    "name": name,
                    "mobile": mobile,
                    "email": email,
                    "class_interested": cls,
                    "source": source,
                    "status": status,
                    "lead_temp": lead_temp,
                    "notes": notes,
                    "inquiry_date": inq_date.isoformat(),
                    "next_followup": next_dt.isoformat()
                }
                ref = db.collection("enquiries").add(doc)[1]
                # create initial follow‑up entry
                add_followup(ref.id, f"Enquiry logged (status={status})", next_dt)
                st.success("✔ Enquiry recorded!")


# ─── Load & Filter ───────────────────────────────────────────────────────────────
df = fetch_enquiries()
if df.empty:
    st.info("No enquiries yet.")
    st.stop()

# filter bar
f1, f2, f3 = st.columns(3)
with f1:
    filt_cls  = st.selectbox("Filter Class", ["All"] + sorted(df["class_interested"].unique().tolist()))
with f2:
    filt_stat = st.selectbox("Filter Status", ["All","New","Contacted","Converted","Not Interested"])
with f3:
    query     = st.text_input("🔎 Search Name or Mobile")

edf = df.copy()
if filt_cls  != "All": edf = edf[edf["class_interested"] == filt_cls]
if filt_stat != "All": edf = edf[edf["status"]           == filt_stat]
if query:
    mask = (
        edf["name"].str.contains(query, case=False, na=False)
        | edf["mobile"].str.contains(query, case=False, na=False)
    )
    edf = edf[mask]


# ─── Table Header ────────────────────────────────────────────────────────────────
headers = [
    "Name","Mobile","Class","Source","Status",
    "Lead Temp","Inquiry Date","Next Follow‑Up",
    "# Follow‑Ups","Actions"
]
cols = st.columns(len(headers))
for i, h in enumerate(headers):
    cols[i].markdown(f"**{h}**")


# ─── Table Rows w/ Inline Follow‑Up Form ─────────────────────────────────────────
if "open_fu" not in st.session_state:
    st.session_state.open_fu = None

for _, row in edf.iterrows():
    cols = st.columns(len(headers))

    # fill basic cells
    cols[0].write(row["name"])
    cols[1].write(row["mobile"])
    cols[2].write(row["class_interested"])
    cols[3].write(row.get("source",""))
    cols[4].write(row.get("status",""))
    cols[5].write(row.get("lead_temp",""))

    cols[6].write(row.get("inquiry_date",""))

    # nicely format Next FU
    try:
        nfu = datetime.fromisoformat(row.get("next_followup",""))
        nfu_str = nfu.strftime("%Y‑%m‑%d %H:%M")
    except:
        nfu_str = row.get("next_followup","")
    cols[7].write(nfu_str)

    cols[8].write(row.get("follow_up_count",0))

    # 🔘 Add Follow‑Up button
    if cols[9].button("➕ Add Follow‑Up", key=f"btn_{row['id']}"):
        st.session_state.open_fu = row["id"]

    # inline follow‑up details & form
    if st.session_state.open_fu == row["id"]:
        st.markdown("---")
        st.markdown(f"#### Previous Follow‑Ups for {row['name']}")
        # list history
        fus = (
            db.collection("enquiries")
              .document(row["id"])
              .collection("followups")
              .order_by("timestamp")
              .stream()
        )
        for fdoc in fus:
            f = fdoc.to_dict()
            ts = f.get("timestamp","")
            cm = f.get("comment","")
            nf = f.get("next_followup","")
            st.write(f"- **{ts}** → {cm} _(Next: {nf})_")

        # the inline form itself
        with st.form(f"fu_form_{row['id']}"):
            st.markdown("**Add Follow‑Up**")
            comment      = st.text_area("Comment")
            dt_date      = st.date_input("Next Follow‑Up Date", date.today())
            dt_time      = st.time_input("Next Follow‑Up Time", datetime.now().time())
            submit_fu    = st.form_submit_button("Save Follow‑Up")
            if submit_fu:
                if comment.strip():
                    next_dt = datetime.combine(dt_date, dt_time)
                    add_followup(row["id"], comment.strip(), next_dt)
                    st.success("✔ Follow‑up saved.")
                    st.session_state.open_fu = None
                else:
                    st.error("Please enter a comment.")

        st.markdown("---")
