import streamlit as st

if "id_token" not in st.session_state:
    st.error("Please log in first.")
    st.stop()
if st.session_state.get("role") != "Front Office":
    st.error("Access denied: Front Office only.")
    st.stop()


# File: pages/3_fee_due_list.py

import streamlit as st
import os
import base64
from datetime import datetime, date
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import firebase_admin
from firebase_admin import credentials, firestore

# ─── Firebase Init ───────────────────────────────────────────────────────────────
if not firebase_admin._apps:
    cred = credentials.Certificate("D:/wisdom/wisdom-schools-firebase-adminsdk-fbsvc-971bbaec20.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

# ─── Paths & Counter Doc ─────────────────────────────────────────────────────────
RECEIPT_DIR = "D:/wisdom/due collection receipt book"
os.makedirs(RECEIPT_DIR, exist_ok=True)

COUNTER_DOC = db.collection("metadata").document("counters")

def get_next_receipt_no():
    """Atomically increment last_receipt_no and return the new value."""
    transaction = db.transaction()

    @firestore.transactional
    def _incr(txn):
        snap = COUNTER_DOC.get(transaction=txn)
        last = snap.get("last_receipt_no") or 10000
        new = int(last) + 1
        txn.update(COUNTER_DOC, {"last_receipt_no": new})
        return new

    return _incr(transaction)

# ─── Receipt PDF Builder ─────────────────────────────────────────────────────────
def build_receipt_pdf(student, amt, mode, next_due, rno, new_balance):
    filename = f"REC{rno:05d}.pdf"
    path = os.path.join(RECEIPT_DIR, filename)
    doc = SimpleDocTemplate(path, pagesize=A4)
    styles = getSampleStyleSheet()
    elems = []

    # Logo
    logo = "D:/wisdom/wisdom logo.png"
    if os.path.exists(logo):
        elems.append(RLImage(logo, width=80, height=80))
    elems.append(Spacer(1, 12))

    elems.append(Paragraph(f"<b>Wisdom Schools</b>", styles["Title"]))
    elems.append(Spacer(1, 6))
    elems.append(Paragraph(f"Fee Receipt #{rno}", styles["Heading2"]))
    elems.append(Spacer(1, 12))

    # Get fee_due_date with fallback
    due_date = student.get("fee_due_date", "Not Set")
    if isinstance(due_date, datetime):
        due_date = due_date.strftime("%Y-%m-%d")
        
    data = [
        ["Student", student.get("name", ""), "Adm No", student.get("admission_no", "")],
        ["Class/Section", f"{student.get('class', '')} / {student.get('section', '')}", 
         "Due Date", due_date],
        ["Amount Paid (₹)", f"{amt:.2f}", "Mode", mode],
        ["New Balance (₹)", f"{new_balance:.2f}", "Next Due", next_due.isoformat()],
    ]
    
    tbl = Table(data, colWidths=[120, 140, 100, 140])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    elems.append(tbl)
    elems.append(Spacer(1, 30))

    elems.append(Paragraph("_______________________                _______________________",
                           styles["Normal"]))
    elems.append(Paragraph("Accounts Signature                       Principal Signature",
                           styles["Normal"]))

    doc.build(elems)
    return path, filename

# ─── Transactional Student Update ────────────────────────────────────────────────
def update_student_balance(student_ref, amount, next_due):
    @firestore.transactional
    def _transaction(txn, student_ref, amount):
        snap = student_ref.get(transaction=txn)
        student_data = snap.to_dict()
        
        current_paid = student_data.get("paid", 0)
        current_balance = student_data.get("balance", 0)
        
        if amount > current_balance:
            raise ValueError("Payment amount exceeds current balance")
            
        new_paid = current_paid + amount
        new_balance = current_balance - amount
        
        update_data = {
            "paid": new_paid,
            "balance": new_balance,
        }
        
        # Only update fee_due_date if field exists
        if "fee_due_date" in student_data:
            update_data["fee_due_date"] = next_due.isoformat()
        
        txn.update(student_ref, update_data)
        return new_paid, new_balance
    
    return _transaction(db.transaction(), student_ref, amount)

# ─── Page Setup ─────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Fee Due List", layout="wide")
st.title("💳 Fee Due List")

# Initialize session state
if 'receipt_data' not in st.session_state:
    st.session_state.receipt_data = None

# ─── Fetch Due Students ─────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner="Fetching due students...")
def get_due_students():
    docs = db.collection("students").where("balance", ">", 0).stream()
    return [doc.to_dict() for doc in docs]

due_students = get_due_students()
if not due_students:
    st.success("✅ No dues – all students fully paid.")
    st.stop()

df = pd.DataFrame(due_students)

# ─── Student Selection ──────────────────────────────────────────────────────────
student_options = {f"{s.get('name', '')} ({s.get('admission_no', '')})": s for s in due_students}
selected_student_key = st.selectbox(
    "👤 Select Student",
    options=[""] + list(student_options.keys()),
    index=0
)

# ─── Payment Section ────────────────────────────────────────────────────────────
if selected_student_key and selected_student_key in student_options:
    student = student_options[selected_student_key]
    
    with st.form(key="payment_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader(f"Payment Details for {student.get('name', '')}")
            current_balance = st.number_input(
                "Current Balance (₹)",
                value=float(student.get("balance", 0)),
                disabled=True
            )
            amount = st.number_input(
                "Amount to Pay (₹)",
                min_value=1.0,
                max_value=float(student.get("balance", 0)),
                step=1.0
            )
            mode = st.selectbox(
                "Payment Mode",
                ["Cash", "Online Transfer", "Cheque", "UPI", "Card"]
            )
            
        with col2:
            st.subheader("Payment Schedule")
            next_due = st.date_input(
                "Next Due Date",
                min_value=date.today()
            )
            remarks = st.text_area("Remarks")
        
        if st.form_submit_button("💳 Process Payment"):
            try:
                receipt_no = get_next_receipt_no()
                student_ref = db.collection("students").document(student.get("admission_no", ""))
                new_paid, new_balance = update_student_balance(student_ref, amount, next_due)
                
                receipt_path, receipt_filename = build_receipt_pdf(
                    student=student,
                    amt=amount,
                    mode=mode,
                    next_due=next_due,
                    rno=receipt_no,
                    new_balance=new_balance
                )
                
                # Store receipt in Firestore
                receipt_data = {
                    "amount": amount,
                    "timestamp": datetime.now().isoformat(),
                    "mode": mode,
                    "next_due": next_due.isoformat(),
                    "receipt_no": receipt_no,
                    "remarks": remarks,
                    "pdf_path": receipt_path
                }
                student_ref.collection("receipts").add(receipt_data)
                
                # Store PDF content in session state
                with open(receipt_path, "rb") as f:
                    st.session_state.receipt_data = {
                        "content": f.read(),
                        "filename": receipt_filename
                    }
                
                st.success(f"Successfully processed ₹{amount:.2f} payment!")
                st.balloons()
                get_due_students.clear()

            except Exception as e:
                st.error(f"Payment failed: {str(e)}")
                st.session_state.receipt_data = None

# ─── Receipt Download ───────────────────────────────────────────────────────────
if st.session_state.receipt_data:
    st.download_button(
        label="⬇️ Download Receipt",
        data=st.session_state.receipt_data["content"],
        file_name=st.session_state.receipt_data["filename"],
        mime="application/pdf",
        key=f"download_{datetime.now().timestamp()}"
    )
    st.session_state.receipt_data = None

# ─── Due List Display ───────────────────────────────────────────────────────────
st.markdown("### 📋 Current Due List")

def make_receipt_links(adm_no):
    try:
        receipts_ref = db.collection("students").document(adm_no).collection("receipts")
        receipts = [r.to_dict() for r in receipts_ref.stream()]
        
        if not receipts:
            return "—"
            
        valid_receipts = sorted(
            [r for r in receipts if 'timestamp' in r and 'pdf_path' in r],
            key=lambda x: x["timestamp"],
            reverse=True
        )
        
        links = []
        for idx, receipt in enumerate(valid_receipts, 1):
            if os.path.exists(receipt["pdf_path"]):
                with open(receipt["pdf_path"], "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                    filename = os.path.basename(receipt["pdf_path"])
                    links.append(
                        f'<a href="data:application/pdf;base64,{b64}" '
                        f'download="{filename}" style="margin-right:10px;">'
                        f'Receipt {idx}</a>'
                    )
        
        return " ".join(links) if links else "—"
    except Exception as e:
        return "—"


# Safe DataFrame handling
safe_columns = ["name", "admission_no", "class", "section", "balance", "father_mobile"]
if "fee_due_date" in df.columns:
    safe_columns.insert(4, "fee_due_date")

display_df = df[safe_columns].copy()
display_df["balance"] = display_df["balance"].apply(lambda x: f"₹{x:.2f}")
display_df["Receipts"] = display_df["admission_no"].apply(make_receipt_links)

# HTML Table
html = display_df.to_html(escape=False, index=False)
st.markdown(html.replace("&lt;", "<").replace("&gt;", ">"), unsafe_allow_html=True)

# CSV Export
csv_columns = safe_columns.copy()
if "Receipts" in csv_columns:
    csv_columns.remove("Receipts")
    
st.download_button(
    "📥 Export Due List as CSV",
    data=df[csv_columns].to_csv(index=False),
    file_name="fee_due_list.csv",
    mime="text/csv"
)