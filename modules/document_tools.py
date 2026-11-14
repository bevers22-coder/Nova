from io import BytesIO
import re
from xml.sax.saxutils import escape


EXPORTS = {
    "Markdown": (".md", "text/markdown"),
    "Plain text": (".txt", "text/plain"),
    "Word document": (".docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    "PDF": (".pdf", "application/pdf"),
}


def export_document(title: str, content: str, file_type: str) -> tuple[bytes, str, str]:
    if file_type not in EXPORTS:
        raise ValueError("Choose a supported export format.")
    if not str(content).strip():
        raise ValueError("Document content cannot be empty.")

    extension, mime_type = EXPORTS[file_type]
    normalized_title = re.sub(r"[^A-Za-z0-9._-]+", "-", title.strip()).strip("-")
    filename = (normalized_title or "nova-document")[:100] + extension

    if file_type == "Markdown":
        payload = content.encode("utf-8")
    elif file_type == "Plain text":
        payload = _strip_markdown(content).encode("utf-8")
    elif file_type == "Word document":
        payload = _make_docx(title, content)
    else:
        payload = _make_pdf(title, content)
    return payload, filename, mime_type


def _strip_markdown(content: str) -> str:
    lines = []
    for line in content.splitlines():
        clean = re.sub(r"^\s{0,3}#{1,6}\s+", "", line)
        clean = re.sub(r"^\s*[-*+]\s+", "• ", clean)
        clean = re.sub(r"\*\*(.+?)\*\*|__(.+?)__", lambda m: m.group(1) or m.group(2), clean)
        clean = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)|_([^_]+)_", lambda m: m.group(1) or m.group(2), clean)
        lines.append(clean)
    return "\n".join(lines)


def _make_docx(title: str, content: str) -> bytes:
    from docx import Document

    document = Document()
    document.add_heading(title.strip() or "NOVA Document", level=0)
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            document.add_paragraph()
        elif stripped.startswith("### "):
            document.add_heading(stripped[4:], level=3)
        elif stripped.startswith("## "):
            document.add_heading(stripped[3:], level=2)
        elif stripped.startswith("# "):
            document.add_heading(stripped[2:], level=1)
        elif re.match(r"^[-*+]\s+", stripped):
            document.add_paragraph(re.sub(r"^[-*+]\s+", "", stripped), style="List Bullet")
        else:
            document.add_paragraph(_strip_markdown(stripped))
    output = BytesIO()
    document.save(output)
    return output.getvalue()


def _make_pdf(title: str, content: str) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title=title.strip() or "NOVA Document",
    )
    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "NovaBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#17212b"),
        spaceAfter=7,
    )
    story = [Paragraph(escape(title.strip() or "NOVA Document"), styles["Title"]), Spacer(1, 14)]
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            story.append(Spacer(1, 7))
            continue
        heading = re.match(r"^(#{1,3})\s+(.*)", stripped)
        if heading:
            story.append(Paragraph(escape(heading.group(2)), styles[f"Heading{len(heading.group(1))}"]))
            continue
        bullet = re.match(r"^[-*+]\s+(.*)", stripped)
        text = f"&#8226;&nbsp;&nbsp;{escape(bullet.group(1))}" if bullet else escape(stripped)
        story.append(Paragraph(text, body))
    document.build(story)
    return output.getvalue()
