import streamlit as st

if "id_token" not in st.session_state:
    st.error("Please log in first.")
    st.stop()
if st.session_state.get("role") != "Front Office":
    st.error("Access denied: Front Office only.")
    st.stop()

import os
import base64
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
import firebase_admin
from firebase_admin import credentials, firestore, initialize_app

# ─── Firebase init ───────────────────────────────────────────────────────────────
if not firebase_admin._apps:
    cred = credentials.Certificate(
        "D:/wisdom/wisdom-schools-firebase-adminsdk-fbsvc-971bbaec20.json"
    )
    initialize_app(cred)
db = firestore.client()

# ─── Helpers ─────────────────────────────────────────────────────────────────────
def load_students():
    """Fetch all students as a list of dicts."""
    return [doc.to_dict() for doc in db.collection("students").stream()]

def build_registration_pdf(student):
    """Return path to registration-form PDF, building it if needed."""
    out_dir = "D:/wisdom/Registration forms"
    os.makedirs(out_dir, exist_ok=True)
    adm = student.get("admission_no", "unknown")
    path = os.path.join(out_dir, f"{adm}_form.pdf")
    if os.path.exists(path):
        return path

    doc = SimpleDocTemplate(
        path, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=20*mm, bottomMargin=20*mm
    )
    styles = getSampleStyleSheet()
    title_style    = ParagraphStyle("Title", parent=styles["Heading1"], alignment=1, fontSize=18)
    subtitle_style = ParagraphStyle("Subtitle", parent=styles["Heading2"], alignment=1, fontSize=14)
    normal         = styles["Normal"]
    small          = ParagraphStyle("Small", parent=normal, fontSize=9)

    elems = []
    # Logo
    logo = "D:/wisdom/wisdom logo.png"
    if os.path.exists(logo):
        elems.append(RLImage(logo, width=50*mm, height=25*mm, hAlign="CENTER"))
        elems.append(Spacer(1, 6))

    # Title
    elems.append(Paragraph("🎓 Wisdom Schools", title_style))
    elems.append(Paragraph("Student Registration Form", subtitle_style))
    elems.append(Spacer(1, 12))

    # Photo (if any)
    photo = student.get("photo_path", "")
    if isinstance(photo, str) and os.path.exists(photo):
        elems.append(RLImage(photo, width=30*mm, height=40*mm, hAlign="RIGHT"))
    elems.append(Spacer(1, 6))

    # Data table
    data = [
        ["Name", student.get("name",""), "Admission No", student.get("admission_no","")],
        ["Class", student.get("class",""), "Section", student.get("section","")],
        ["DOB", student.get("dob",""), "Gender", student.get("gender","")],
        ["Father Name", student.get("father_name",""), "Mobile", student.get("father_mobile","")],
        ["Mother Name", student.get("mother_name",""), "Mobile", student.get("mother_mobile","")],
        ["Email", student.get("parent_email",""), "Address", Paragraph(student.get("address",""), normal)],
        ["Total Fee", f"₹{student.get('total_fee',0):.2f}", "Paid", f"₹{student.get('paid',0):.2f}"],
        ["Balance", f"₹{student.get('balance',0):.2f}", "Registration Date", student.get("registration_date","")],
    ]
    table = Table(data, colWidths=[30*mm,60*mm,30*mm,60*mm])
    table.setStyle(TableStyle([
        ("BOX",        (0,0), (-1,-1), 1, colors.HexColor("#004466")),
        ("GRID",       (0,0), (-1,-1), 0.5, colors.HexColor("#004466")),
        ("BACKGROUND", (0,0), (-1,0),   colors.lightgrey),
        ("FONTNAME",   (0,0), (-1,0),   "Helvetica-Bold"),
        ("VALIGN",     (0,0), (-1,-1),  "MIDDLE"),
        *[("BACKGROUND", (0,i), (-1,i), colors.whitesmoke) for i in range(1, len(data), 2)]
    ]))
    elems.append(table)
    elems.append(Spacer(1, 24))

    # Signatures
    sig = Table(
        [[Paragraph("______________________<br/>Principal Signature", small),
          Paragraph("Parent Signature<br/>______________________", small)]],
        colWidths=[80*mm,80*mm]
    )
    sig.setStyle(TableStyle([("ALIGN",(0,0),(-1,-1),"CENTER"), ("VALIGN",(0,0),(-1,-1),"TOP")]))
    elems.append(sig)

    elems.append(Spacer(1, 12))
    elems.append(Paragraph(
        f"<i>Generated on: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}</i>",
        ParagraphStyle("Timestamp", parent=small, alignment=2)
    ))

    doc.build(elems)
    return path

def make_receipt_links(adm_no):
    """Return HTML `<a>` links to all receipts for this admission_no."""
    receipts = db \
      .collection("students") \
      .document(adm_no) \
      .collection("receipts") \
      .stream()

    links = []
    for idx, doc in enumerate(receipts, start=1):
        r = doc.to_dict()
        pdf_path = r.get("pdf_path")
        if pdf_path and os.path.exists(pdf_path):
            b64 = base64.b64encode(open(pdf_path, "rb").read()).decode()
            fn  = os.path.basename(pdf_path)
            links.append(
                f'<a href="data:application/pdf;base64,{b64}" download="{fn}">'
                f"Receipt {idx}</a>"
            )
    return " | ".join(links) if links else "—"

# ─── Streamlit UI ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Registered Students", layout="wide")
st.title("📋 Registered Students")

# Load and display
df = pd.DataFrame(load_students())

# ─── Filters ────────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
with c1:
    fclass = st.selectbox("📚 Class", ["All"] + sorted(df['class'].dropna().astype(str).unique()))
with c2:
    fsect  = st.selectbox("🟡 Section", ["All"] + sorted(df['section'].dropna().astype(str).unique()))
with c3:
    fstat  = st.selectbox("💳 Status", ["All","Paid","Due"])
with c4:
    search = st.text_input("🔍 Search Name/Adm No/Mobile")

# ─── Apply Filters ───────────────────────────────────────────────────────────────
flt = df.copy()
if fclass != "All":
    flt = flt[flt['class'].astype(str)==fclass]
if fsect  != "All":
    flt = flt[flt['section'].astype(str)==fsect]
if fstat  != "All":
    if fstat == "Paid":
        flt = flt[flt['balance']==0]
    else:  # Due
        flt = flt[flt['balance']>0]
if search:
    s = search.lower()
    flt = flt[
        flt['name'].str.lower().str.contains(s, na=False) |
        flt['admission_no'].str.lower().str.contains(s, na=False) |
        flt['father_mobile'].astype(str).str.contains(search)
    ]

# ─── Build HTML Table ───────────────────────────────────────────────────────────
css = """
<style>
  table {width:100%;border-collapse:collapse;font-family:sans-serif;}
  th,td {border:1px solid #004466;padding:6px;text-align:center;}
  th {background:#004466;color:#fff;}
  .Paid{background:#d4edda;}   /* paid = green */
  .Due {background:#f8d7da;}   /* due  = pink  */
  img.thumb{width:40px;height:50px;object-fit:cover;border-radius:4px;}
  a.btn-dl{background:#004466;color:#fff;padding:4px 8px;border-radius:4px;
           text-decoration:none;margin-right:4px;}
  a.btn-vw{background:#eaeaea;color:#004466;padding:4px 8px;border-radius:4px;
           text-decoration:none;}
  td.receipt a {margin:0 4px;}
</style>
"""
headers = [
    "Photo","Name","Adm No","Class","Section",
    "Reg Date","Mobile","Total","Paid","Balance",
    "Actions","Receipt"
]
html = css + "<table><tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr>"

for s in flt.to_dict("records"):
    status_cls = "Paid" if s.get("balance",0)==0 else "Due"

    # thumbnail
    thumb = "—"
    p = s.get("photo_path","")
    if isinstance(p,str) and os.path.exists(p):
        b64 = base64.b64encode(open(p,"rb").read()).decode()
        thumb = f"<img src='data:image/png;base64,{b64}' class='thumb'/>"

    # registration PDF buttons
    pdfp = build_registration_pdf(s)
    if os.path.exists(pdfp):
        b64    = base64.b64encode(open(pdfp,"rb").read()).decode()
        fname  = os.path.basename(pdfp)
        dl_btn = f"<a class='btn-dl' href='data:application/pdf;base64,{b64}' download='{fname}'>Download</a>"
        vw_btn = f"<a class='btn-vw' href='data:application/pdf;base64,{b64}' target='_blank'>View</a>"
    else:
        dl_btn = vw_btn = "—"

    # receipt links
    rec_links = make_receipt_links(s['admission_no'])

    html += (
        f"<tr class='{status_cls}'>"
        f"<td>{thumb}</td>"
        f"<td>{s.get('name','')}</td>"
        f"<td>{s.get('admission_no','')}</td>"
        f"<td>{s.get('class','')}</td>"
        f"<td>{s.get('section','')}</td>"
        f"<td>{s.get('registration_date','')}</td>"
        f"<td>{s.get('father_mobile','')}</td>"
        f"<td>₹{s.get('total_fee',0):.2f}</td>"
        f"<td>₹{s.get('paid',0):.2f}</td>"
        f"<td>₹{s.get('balance',0):.2f}</td>"
        f"<td>{dl_btn}{vw_btn}</td>"
        f"<td class='receipt'>{rec_links}</td>"
        "</tr>"
    )

html += "</table>"

# ─── Render ─────────────────────────────────────────────────────────────────────
components.html(html, height=650, scrolling=True)
