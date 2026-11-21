"""Generate a professional 1-page DOCX and HTML submission document for Nigehbaan AI."""

from __future__ import annotations
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DOCX = ROOT / "Project_Deployment_Submission_Nigehbaan_AI.docx"
OUTPUT_HTML = ROOT / "Project_Deployment_Submission_Nigehbaan_AI.html"

def set_cell_shading(cell, fill_hex: str):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = tcPr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tcPr.append(shd)
    shd.set(qn("w:fill"), fill_hex)

def set_cell_margins(cell, top=60, bottom=60, left=100, right=100):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement("w:tcMar")
    for side, value in [("top", top), ("bottom", bottom), ("left", left), ("right", right)]:
        node = OxmlElement(f"w:{side}")
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")
        tcMar.append(node)
    tcPr.append(tcMar)

def create_docx():
    doc = Document()
    
    # 1-page compact margins
    section = doc.sections[0]
    section.top_margin = Inches(0.45)
    section.bottom_margin = Inches(0.45)
    section.left_margin = Inches(0.65)
    section.right_margin = Inches(0.65)
    
    # University Header
    p_uni = doc.add_paragraph()
    p_uni.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_uni.paragraph_format.space_before = Pt(0)
    p_uni.paragraph_format.space_after = Pt(1)
    r_uni = p_uni.add_run("NED UNIVERSITY OF ENGINEERING & TECHNOLOGY")
    r_uni.bold = True
    r_uni.font.name = "Arial"
    r_uni.font.size = Pt(12)
    r_uni.font.color.rgb = RGBColor(27, 54, 93) # Navy
    
    p_dept = doc.add_paragraph()
    p_dept.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_dept.paragraph_format.space_after = Pt(6)
    r_dept = p_dept.add_run("Department of Computer Science & Information Technology · Fall 2026")
    r_dept.font.name = "Arial"
    r_dept.font.size = Pt(9)
    r_dept.font.color.rgb = RGBColor(80, 80, 80)
    
    # Document Badge Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_after = Pt(8)
    r_title = p_title.add_run("PROJECT DEPLOYMENT SUBMISSION")
    r_title.bold = True
    r_title.font.name = "Arial"
    r_title.font.size = Pt(13)
    r_title.font.color.rgb = RGBColor(192, 0, 0) # Deep Red
    
    # Metadata Table
    table_meta = doc.add_table(rows=3, cols=2)
    table_meta.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_meta.autofit = False
    
    col_widths = [Inches(1.8), Inches(5.4)]
    meta_data = [
        ("Course Code & Title:", "CT-361: Artificial Intelligence & Expert Systems (AIES)"),
        ("Project Title:", "Nigehbaan AI — Multimodal Roman Urdu Scam & Abuse Detection System"),
        ("Class Section:", "BS CS — Section B"),
    ]
    
    for i, (label, val) in enumerate(meta_data):
        row = table_meta.rows[i]
        c0, c1 = row.cells[0], row.cells[1]
        c0.width, c1.width = col_widths[0], col_widths[1]
        set_cell_shading(c0, "F1F5F9")
        set_cell_shading(c1, "FAFAFA")
        set_cell_margins(c0, 50, 50, 80, 80)
        set_cell_margins(c1, 50, 50, 80, 80)
        
        p0 = c0.paragraphs[0]
        p0.paragraph_format.space_after = Pt(0)
        r0 = p0.add_run(label)
        r0.bold = True
        r0.font.name = "Arial"
        r0.font.size = Pt(9)
        r0.font.color.rgb = RGBColor(30, 41, 59)
        
        p1 = c1.paragraphs[0]
        p1.paragraph_format.space_after = Pt(0)
        r1 = p1.add_run(val)
        if i == 1:
            r1.bold = True
        r1.font.name = "Arial"
        r1.font.size = Pt(9)
        r1.font.color.rgb = RGBColor(15, 23, 42)
        
    doc.add_paragraph().paragraph_format.space_after = Pt(3)
    
    # 1. Group Members Section
    h_members = doc.add_paragraph()
    h_members.paragraph_format.space_before = Pt(2)
    h_members.paragraph_format.space_after = Pt(2)
    r_hm = h_members.add_run("1. Group Members (Section B)")
    r_hm.bold = True
    r_hm.font.name = "Arial"
    r_hm.font.size = Pt(10)
    r_hm.font.color.rgb = RGBColor(27, 54, 93)
    
    table_members = doc.add_table(rows=5, cols=3)
    table_members.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_members.autofit = False
    
    m_widths = [Inches(0.9), Inches(2.2), Inches(4.1)]
    members = [
        ("S. No.", "Roll Number", "Student Full Name"),
        ("1", "CT-24224", "Muhammad Taha Farrukh"),
        ("2", "CT-24221", "Muhammad Saad"),
        ("3", "CT-24227", "UsaidUllah Qureshi"),
        ("4", "CT-24244", "Uzair Ahmed"),
    ]
    
    for r_idx, row_vals in enumerate(members):
        row = table_members.rows[r_idx]
        for c_idx, val in enumerate(row_vals):
            cell = row.cells[c_idx]
            cell.width = m_widths[c_idx]
            set_cell_margins(cell, 45, 45, 70, 70)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(val)
            r.font.name = "Arial"
            r.font.size = Pt(8.5)
            if r_idx == 0:
                set_cell_shading(cell, "1B365D")
                r.bold = True
                r.font.color.rgb = RGBColor(255, 255, 255)
            else:
                set_cell_shading(cell, "F8FAFC" if r_idx % 2 == 1 else "FFFFFF")
                if c_idx == 1:
                    r.bold = True
                r.font.color.rgb = RGBColor(30, 41, 59)
                
    doc.add_paragraph().paragraph_format.space_after = Pt(3)
    
    # 2. Deployment Links Section
    h_links = doc.add_paragraph()
    h_links.paragraph_format.space_before = Pt(2)
    h_links.paragraph_format.space_after = Pt(2)
    r_hl = h_links.add_run("2. Public Deployment & Git Repository Links")
    r_hl.bold = True
    r_hl.font.name = "Arial"
    r_hl.font.size = Pt(10)
    r_hl.font.color.rgb = RGBColor(27, 54, 93)
    
    table_links = doc.add_table(rows=4, cols=2)
    table_links.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_links.autofit = False
    l_widths = [Inches(2.2), Inches(5.0)]
    
    links_data = [
        ("Frontend Web App (Vercel):", "https://nighebaan-ai.vercel.app"),
        ("Backend API Server (Render):", "https://nighebaan-ai.onrender.com"),
        ("Interactive API Docs (Swagger):", "https://nighebaan-ai.onrender.com/docs"),
        ("GitHub Repository (Full Codebase):", "https://github.com/MTahaFarrukh/nighebaan-ai"),
    ]
    
    for r_idx, (component, link) in enumerate(links_data):
        row = table_links.rows[r_idx]
        c0, c1 = row.cells[0], row.cells[1]
        c0.width, c1.width = l_widths[0], l_widths[1]
        set_cell_shading(c0, "F1F5F9")
        set_cell_shading(c1, "FFFFFF")
        set_cell_margins(c0, 45, 45, 70, 70)
        set_cell_margins(c1, 45, 45, 70, 70)
        
        p0 = c0.paragraphs[0]
        p0.paragraph_format.space_after = Pt(0)
        r0 = p0.add_run(component)
        r0.bold = True
        r0.font.name = "Arial"
        r0.font.size = Pt(8.5)
        r0.font.color.rgb = RGBColor(30, 41, 59)
        
        p1 = c1.paragraphs[0]
        p1.paragraph_format.space_after = Pt(0)
        r1 = p1.add_run(link)
        r1.font.name = "Arial"
        r1.font.size = Pt(8.5)
        r1.font.color.rgb = RGBColor(2, 132, 199)
        r1.underline = True
        
    doc.add_paragraph().paragraph_format.space_after = Pt(3)
    
    # 3. WhatsApp Execution & .env Setup Guide
    h_note = doc.add_paragraph()
    h_note.paragraph_format.space_before = Pt(2)
    h_note.paragraph_format.space_after = Pt(2)
    r_hn = h_note.add_run("3. WhatsApp Bot (Baileys) Terminal Setup & .env Configuration Guide")
    r_hn.bold = True
    r_hn.font.name = "Arial"
    r_hn.font.size = Pt(10)
    r_hn.font.color.rgb = RGBColor(27, 54, 93)
    
    p_exp = doc.add_paragraph()
    p_exp.paragraph_format.space_after = Pt(2)
    p_exp.paragraph_format.line_spacing = 1.1
    r_exp = p_exp.add_run(
        "WhatsApp monitoring uses @whiskeysockets/baileys. Baileys requires a 24/7 persistent WebSocket connection, "
        "local multi-file session storage (auth_baileys), and a residential IP to prevent WhatsApp datacenter bans. "
        "Hence, the bot runs locally via terminal and dispatches messages to the live cloud Render API."
    )
    r_exp.font.name = "Arial"
    r_exp.font.size = Pt(8.2)
    r_exp.font.color.rgb = RGBColor(50, 50, 50)
    
    # Table for Git Execution & .env Details
    table_guide = doc.add_table(rows=2, cols=2)
    table_guide.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_guide.autofit = False
    g_widths = [Inches(3.4), Inches(3.8)]
    
    # Left Cell: Git execution commands
    c_left = table_guide.rows[0].cells[0]
    c_left.width = g_widths[0]
    set_cell_shading(c_left, "F8FAFC")
    set_cell_margins(c_left, 50, 50, 60, 60)
    p_gl = c_left.paragraphs[0]
    p_gl.paragraph_format.space_after = Pt(2)
    r_glt = p_gl.add_run("A. Terminal Execution Commands:\n")
    r_glt.bold = True
    r_glt.font.name = "Arial"
    r_glt.font.size = Pt(8.2)
    r_glt.font.color.rgb = RGBColor(27, 54, 93)
    
    cmd_text = (
        "git clone https://github.com/MTahaFarrukh/nighebaan-ai.git\n"
        "cd nighebaan-ai/whatsapp\n"
        "npm install\n"
        "npm run dev\n"
        "(Scan terminal QR code via WhatsApp Linked Devices)"
    )
    r_cmd = p_gl.add_run(cmd_text)
    r_cmd.font.name = "Consolas"
    r_cmd.font.size = Pt(7.8)
    r_cmd.font.color.rgb = RGBColor(180, 0, 0)
    
    # Right Cell: .env configuration instructions
    c_right = table_guide.rows[0].cells[1]
    c_right.width = g_widths[1]
    set_cell_shading(c_right, "F8FAFC")
    set_cell_margins(c_right, 50, 50, 60, 60)
    p_gr = c_right.paragraphs[0]
    p_gr.paragraph_format.space_after = Pt(2)
    r_grt = p_gr.add_run("B. File: whatsapp/.env (Configuration Variables):\n")
    r_grt.bold = True
    r_grt.font.name = "Arial"
    r_grt.font.size = Pt(8.2)
    r_grt.font.color.rgb = RGBColor(27, 54, 93)
    
    env_text = (
        'WHATSAPP_API_KEY="render-par-rakha-hua-32-char-key"\n'
        'WHATSAPP_DEMO_JID="923001234567@s.whatsapp.net"\n'
        'WHATSAPP_GUARDIAN_JID="923117654321@s.whatsapp.net"\n'
        'WHATSAPP_OWNER_OPT_IN="true"\n'
        'DRY_RUN="true"   # true for logs, false for live alerts\n'
        'BACKEND_API_URL="https://nighebaan-ai.onrender.com/api"'
    )
    r_env = p_gr.add_run(env_text)
    r_env.font.name = "Consolas"
    r_env.font.size = Pt(7.5)
    r_env.font.color.rgb = RGBColor(15, 23, 42)
    
    # Bottom Merged Row: Privacy note
    row_bot = table_guide.rows[1]
    cell_bot = row_bot.cells[0]
    cell_bot.merge(row_bot.cells[1])
    set_cell_shading(cell_bot, "EFF6FF")
    set_cell_margins(cell_bot, 40, 40, 60, 60)
    p_bot = cell_bot.paragraphs[0]
    p_bot.paragraph_format.space_after = Pt(0)
    r_bot = p_bot.add_run(
        "Privacy & Security Note: Under project privacy guidelines, personal phone numbers and active auth states are strictly gitignored (.gitignore). "
        "Evaluators configure their respective phone numbers in whatsapp/.env prior to execution."
    )
    r_bot.font.name = "Arial"
    r_bot.font.size = Pt(7.8)
    r_bot.font.color.rgb = RGBColor(30, 64, 175)
    
    doc.save(str(OUTPUT_DOCX))
    print(f"Generated DOCX: {OUTPUT_DOCX}")

def create_html():
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Project Deployment Submission - Nigehbaan AI</title>
  <style>
    @page {
      size: A4 portrait;
      margin: 10mm 14mm;
    }
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }
    body {
      font-family: Arial, Helvetica, sans-serif;
      color: #1e293b;
      line-height: 1.3;
      font-size: 12px;
      background: #fff;
    }
    .header {
      text-align: center;
      border-bottom: 2px solid #1b365d;
      padding-bottom: 5px;
      margin-bottom: 8px;
    }
    .header h1 {
      font-size: 16px;
      color: #1b365d;
      font-weight: bold;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 2px;
    }
    .header .sub {
      font-size: 11px;
      color: #475569;
      margin-bottom: 5px;
    }
    .badge {
      display: inline-block;
      background-color: #b91c1c;
      color: white;
      font-weight: bold;
      font-size: 11px;
      padding: 2px 10px;
      border-radius: 3px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .section-title {
      font-size: 12px;
      font-weight: bold;
      color: #1b365d;
      border-left: 3px solid #1b365d;
      padding-left: 6px;
      margin-top: 8px;
      margin-bottom: 4px;
      text-transform: uppercase;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 6px;
      font-size: 11px;
    }
    th, td {
      border: 1px solid #cbd5e1;
      padding: 4px 8px;
      text-align: left;
    }
    th {
      background-color: #1b365d;
      color: white;
      font-weight: bold;
    }
    .meta-table td:first-child {
      width: 25%;
      font-weight: bold;
      background-color: #f1f5f9;
      color: #0f172a;
    }
    .links-table td:first-child {
      width: 32%;
      font-weight: bold;
      background-color: #f1f5f9;
    }
    .links-table a {
      color: #0284c7;
      text-decoration: underline;
      font-weight: 500;
      word-break: break-all;
    }
    .members-table tr:nth-child(even) {
      background-color: #f8fafc;
    }
    .members-table td:nth-child(2) {
      font-weight: bold;
    }
    .guide-grid {
      display: flex;
      gap: 8px;
      margin-bottom: 6px;
    }
    .guide-box {
      flex: 1;
      border: 1px solid #cbd5e1;
      background: #f8fafc;
      border-radius: 3px;
      padding: 6px 8px;
      font-size: 10px;
    }
    .guide-box h4 {
      font-size: 10.5px;
      color: #1b365d;
      margin-bottom: 4px;
      border-bottom: 1px solid #e2e8f0;
      padding-bottom: 2px;
    }
    .code-block {
      font-family: Consolas, monospace;
      font-size: 9.5px;
      color: #0f172a;
      white-space: pre;
      line-height: 1.25;
    }
    .code-cmd {
      color: #b91c1c;
      font-weight: bold;
    }
    .note-banner {
      background-color: #eff6ff;
      border: 1px solid #bfdbfe;
      border-left: 3px solid #2563eb;
      padding: 5px 8px;
      font-size: 9.5px;
      color: #1e40af;
      border-radius: 2px;
    }
    .footer {
      text-align: center;
      font-size: 9px;
      color: #64748b;
      margin-top: 8px;
      border-top: 1px dashed #cbd5e1;
      padding-top: 4px;
    }
  </style>
</head>
<body>

  <div class="header">
    <h1>NED University of Engineering & Technology</h1>
    <div class="sub">Department of Computer Science & Information Technology · Fall 2026 Semester</div>
    <div class="badge">Project Deployment Submission</div>
  </div>

  <table class="meta-table">
    <tr>
      <td>Course Code & Title</td>
      <td><strong>CT-361: Artificial Intelligence & Expert Systems (AIES)</strong></td>
    </tr>
    <tr>
      <td>Project Title</td>
      <td><strong>Nigehbaan AI — Multimodal Roman Urdu Scam & Abuse Detection System</strong></td>
    </tr>
    <tr>
      <td>Class Section</td>
      <td><strong>BS CS — Section B</strong></td>
    </tr>
  </table>

  <div class="section-title">1. Group Members (Section B)</div>
  <table class="members-table">
    <thead>
      <tr>
        <th style="width: 10%;">S. No.</th>
        <th style="width: 32%;">Roll Number</th>
        <th>Student Full Name</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>1</td>
        <td>CT-24224</td>
        <td>Muhammad Taha Farrukh</td>
      </tr>
      <tr>
        <td>2</td>
        <td>CT-24221</td>
        <td>Muhammad Saad</td>
      </tr>
      <tr>
        <td>3</td>
        <td>CT-24227</td>
        <td>UsaidUllah Qureshi</td>
      </tr>
      <tr>
        <td>4</td>
        <td>CT-24244</td>
        <td>Uzair Ahmed</td>
      </tr>
    </tbody>
  </table>

  <div class="section-title">2. Public Deployment & Git Repository Links</div>
  <table class="links-table">
    <tr>
      <td>Frontend Web App (Vercel)</td>
      <td><a href="https://nighebaan-ai.vercel.app">https://nighebaan-ai.vercel.app</a></td>
    </tr>
    <tr>
      <td>Backend API Server (Render)</td>
      <td><a href="https://nighebaan-ai.onrender.com">https://nighebaan-ai.onrender.com</a></td>
    </tr>
    <tr>
      <td>Interactive API Docs (Swagger)</td>
      <td><a href="https://nighebaan-ai.onrender.com/docs">https://nighebaan-ai.onrender.com/docs</a></td>
    </tr>
    <tr>
      <td>GitHub Repository (Codebase)</td>
      <td><a href="https://github.com/MTahaFarrukh/nighebaan-ai">https://github.com/MTahaFarrukh/nighebaan-ai</a></td>
    </tr>
  </table>

  <div class="section-title">3. WhatsApp Bot (Baileys) Terminal Setup & .env Configuration Guide</div>
  <p style="font-size: 10px; color: #475569; margin-bottom: 5px;">
    WhatsApp monitoring uses <strong>@whiskeysockets/baileys</strong>. Because WhatsApp Web requires a persistent 24/7 WebSocket connection, local session auth (<code>auth_baileys</code>), and a residential IP against cloud IP bans, the WhatsApp client runs locally on the terminal and dispatches messages to the live cloud Render API:
  </p>

  <div class="guide-grid">
    <div class="guide-box">
      <h4>A. Terminal Execution (Git Clone & Run)</h4>
      <div class="code-block code-cmd">git clone https://github.com/MTahaFarrukh/nighebaan-ai.git
cd nighebaan-ai/whatsapp
npm install
npm run dev</div>
      <div style="font-size: 9px; color: #64748b; margin-top: 4px;">Scan the QR code printed in the terminal via WhatsApp Linked Devices.</div>
    </div>
    <div class="guide-box">
      <h4>B. Configuration File (whatsapp/.env)</h4>
      <div class="code-block">WHATSAPP_API_KEY="render-par-rakha-hua-32-char-key"
WHATSAPP_DEMO_JID="923001234567@s.whatsapp.net"
WHATSAPP_GUARDIAN_JID="923117654321@s.whatsapp.net"
WHATSAPP_OWNER_OPT_IN="true"
DRY_RUN="true"   # true for logs, false for live alerts
BACKEND_API_URL="https://nighebaan-ai.onrender.com/api"</div>
    </div>
  </div>

  <div class="note-banner">
    <strong>Privacy & Security Note:</strong> Under course privacy rules, personal phone numbers and active auth states are strictly gitignored (<code>.gitignore</code>). Evaluators configure their own recipient numbers in <code>whatsapp/.env</code> prior to running.
  </div>

  <div class="footer">
    Nigehbaan AI · CT-361 Artificial Intelligence & Expert Systems · NED University of Engineering & Technology
  </div>

</body>
</html>
"""
    OUTPUT_HTML.write_text(html_content, encoding="utf-8")
    print(f"Generated HTML: {OUTPUT_HTML}")

if __name__ == "__main__":
    create_docx()
    create_html()
