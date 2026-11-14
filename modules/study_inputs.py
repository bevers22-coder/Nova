import base64
from io import BytesIO
from pathlib import Path


MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_EXTRACTED_CHARACTERS = 40_000
_TEXT_SUFFIXES = {".txt", ".md", ".csv"}
_IMAGE_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


def read_study_upload(filename: str, content: bytes) -> tuple[str, str | None]:
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("Files must be 8 MB or smaller.")
    suffix = Path(filename).suffix.lower()
    if suffix in _TEXT_SUFFIXES:
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise ValueError("Text files must use UTF-8 encoding.") from error
        return text[:MAX_EXTRACTED_CHARACTERS], None
    if suffix == ".docx":
        from docx import Document

        document = Document(BytesIO(content))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
        return text[:MAX_EXTRACTED_CHARACTERS], None
    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages[:50])
        return text[:MAX_EXTRACTED_CHARACTERS], None
    if suffix in _IMAGE_TYPES:
        encoded = base64.b64encode(content).decode("ascii")
        return "", f"data:{_IMAGE_TYPES[suffix]};base64,{encoded}"
    raise ValueError("Supported uploads: TXT, Markdown, CSV, DOCX, PDF, PNG, JPG, and WEBP.")
