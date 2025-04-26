# pages/register_student.py
import streamlit as st

def app():
    st.header("✏️ Register Student")
    # ... your code ...

import streamlit as st

if "id_token" not in st.session_state:
    st.error("Please log in first.")
    st.stop()
if st.session_state.get("role") != "Front Office":
    st.error("Access denied: Front Office only.")
    st.stop()


import streamlit as st
from datetime import date, datetime
import firebase_admin
from firebase_admin import credentials, firestore
import os
import re

# ─── Firebase setup ───────────────────────────────────────────────────────────────
if not firebase_admin._apps:
    cred = credentials.Certificate("D:/wisdom/wisdom-schools-firebase-adminsdk-fbsvc-971bbaec20.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

# ─── Paths & Counters ─────────────────────────────────────────────────────────────
PHOTO_DIR = "D:/wisdom/students photos"
os.makedirs(PHOTO_DIR, exist_ok=True)

BILL_START = 1001  # now starts at 1001
ADM_START  = 1

def next_bill_no():
    docs = db.collection("students") \
             .order_by("bill_no", direction=firestore.Query.DESCENDING) \
             .limit(1).stream()
    last = next(docs, None)
    if last:
        try:
            return int(last.to_dict().get("bill_no", BILL_START - 1)) + 1
        except:
            pass
    return BILL_START

def next_adm_no():
    docs = db.collection("students") \
             .order_by("admission_no", direction=firestore.Query.DESCENDING) \
             .limit(1).stream()
    last = next(docs, None)
    if last:
        try:
            num = int(last.id)
            return f"{num+1:04d}"
        except:
            pass
    return f"{ADM_START:04d}"

# ─── Page config & styling ────────────────────────────────────────────────────────
st.set_page_config(page_title="Register Student", layout="wide")
st.markdown("""
  <style>
    .section {background:#f8f9fa; padding:16px; border-radius:8px; margin-bottom:16px;}
    .section h3 {color:#004466; margin-bottom:8px;}
    .fee-summary {font-size:24px; color:red; font-weight:bold; margin-top:16px;}
  </style>
""", unsafe_allow_html=True)

# ─── Header & Logo ────────────────────────────────────────────────────────────────

st.markdown("<h1 style='text-align:center;'>🎓 Wisdom Schools</h1>", unsafe_allow_html=True)
st.markdown("<h2 style='text-align:center;'>Register Student</h2>", unsafe_allow_html=True)

# ─── Generate fresh IDs ────────────────────────────────────────────────────────────
admission_no = next_adm_no()
bill_no      = str(next_bill_no())
reg_dt       = datetime.now()
st.markdown(
    f"<h4 style='text-align:right;'>Admission No: "
    f"<span style='color:green;'>{admission_no}</span></h4>",
    unsafe_allow_html=True
)

# ─── MAIN FORM ────────────────────────────────────────────────────────────────────
with st.form("student_form"):
    # Student Info
    st.markdown("<div class='section'><h3>👦 Student Information</h3>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        name      = st.text_input("Full Name *")
        dob       = st.date_input("Date of Birth *", date.today())
        gender    = st.selectbox("Gender *", ["","Male","Female","Other"])
        aadhar    = st.text_input("Aadhaar Card Number")
        blood_grp = st.selectbox("Blood Group *", ["","A+","A-","B+","B-","O+","O-","AB+","AB-"])
        prev_sch  = st.text_input("Previous School (if any)")
    with c2:
        st.markdown(f"**Registration Date:** {reg_dt.strftime('%d-%m-%Y %H:%M:%S')}")
        photo = st.file_uploader("Upload Photo *", type=["jpg","png","jpeg"])
        cls_opts = ["","Nursery","LKG","UKG"] + [str(i) for i in range(1,11)]
        sec_opts = ["","A","B","C","D","E"]
        student_class   = st.selectbox("Class *", cls_opts)
        student_section = st.selectbox("Section *", sec_opts)
        # Age
        today = date.today()
        age_years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        st.markdown(f"**Age:** {age_years} years")
    st.markdown("</div>", unsafe_allow_html=True)

    # Parent Info
    st.markdown("<div class='section'><h3>👨‍👩‍👦 Parent Information</h3>", unsafe_allow_html=True)
    f_name   = st.text_input("Father Full Name *")
    f_mobile = st.text_input("Father Mobile *", max_chars=10)
    if f_mobile and not re.fullmatch(r"\d{10}", f_mobile):
        st.error("Father's mobile must be 10 digits.")
    m_name   = st.text_input("Mother Full Name *")
    m_mobile = st.text_input("Mother Mobile *", max_chars=10)
    if m_mobile and not re.fullmatch(r"\d{10}", m_mobile):
        st.error("Mother's mobile must be 10 digits.")
    parent_email = st.text_input("Parent Email")
    address      = st.text_area("Full Address *")
    st.markdown("</div>", unsafe_allow_html=True)

    # Fee Details & Due Date
    st.markdown("<div class='section'><h3>💰 Fee Details</h3>", unsafe_allow_html=True)
    fcol1, fcol2 = st.columns(2)
    with fcol1:
        admission_fee = st.number_input("Admission Fee (₹)", value=0, key="adm_fee")
        school_fee    = st.number_input("School Fee (₹)",     value=0, key="sch_fee")
        book_fee      = st.number_input("Book Fee (₹)",       value=0, key="book_fee")
        uniform_fee   = st.number_input("Uniform Fee (₹)",    value=0, key="uni_fee")
    with fcol2:
        transport_fee = st.number_input("Transport Fee (₹)",  value=0, key="trans_fee")
        lab_fee       = st.number_input("Lab Fee (₹)",        value=0, key="lab_fee")
        discount      = st.number_input("Discount (₹2000 max)", max_value=2000, value=0, key="disc")
        paid          = st.number_input("Fees Paid (₹)",      value=0, key="paid")
        payment_mode  = st.selectbox("Payment Mode *", [
                          "", "Cash", "Cheque", "Online",
                          "Google Pay", "PhonePe", "Paytm", "UPI"
                        ])
        balance_due_date = st.date_input("Balance Due Date *", date.today())

    # compute summary
    total   = admission_fee + school_fee + book_fee + uniform_fee + transport_fee + lab_fee - discount
    balance = total - paid

    st.markdown(
      f"<div class='fee-summary'>"
      f"🧾 Fee Summary: Total ₹{total} | Paid ₹{paid} | Balance ₹{balance}</div>",
      unsafe_allow_html=True
    )
    st.markdown(f"🧾 <b>Bill No:</b> {bill_no}", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # submit
    submitted = st.form_submit_button("📋 Register Student")
    if submitted:
        mandatory = [name, gender, student_class, student_section,
                     f_name, f_mobile, m_name, m_mobile,
                     address, photo, balance_due_date, payment_mode]
        if not all(mandatory):
            st.error("❌ Please fill all required fields (*), upload photo, select due date & payment mode.")
        else:
            ext  = photo.name.rsplit(".",1)[-1]
            fn   = f"{admission_no}_{name.replace(' ','_')}.{ext}"
            pth  = os.path.join(PHOTO_DIR, fn)
            with open(pth,"wb") as fp:
                fp.write(photo.read())

            doc = {
                "name":              name,
                "dob":               dob.isoformat(),
                "gender":            gender,
                "aadhar":            aadhar,
                "blood_group":       blood_grp,
                "previous_school":   prev_sch,
                "father_name":       f_name,
                "father_mobile":     f_mobile,
                "mother_name":       m_name,
                "mother_mobile":     m_mobile,
                "parent_email":      parent_email,
                "address":           address,
                "class":             student_class,
                "section":           student_section,
                "admission_no":      admission_no,
                "bill_no":           bill_no,
                "payment_mode":      payment_mode,
                "admission_fee":     admission_fee,
                "school_fee":        school_fee,
                "book_fee":          book_fee,
                "uniform_fee":       uniform_fee,
                "transport_fee":     transport_fee,
                "lab_fee":           lab_fee,
                "discount":          discount,
                "paid":              paid,
                "total_fee":         total,
                "balance":           balance,
                "balance_due_date":  balance_due_date.isoformat(),
                "registration_date": reg_dt.isoformat(),
                "photo_path":        pth
            }
            db.collection("students").document(admission_no).set(doc)
            st.success("✅ Registration complete! You can now view the student in the Registered Students list.")
