"""Local document parsing boundary.

The parser returns page text only. OCR can be plugged into this boundary later
without changing storage, authorization, or citation handling.
"""
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree

ALLOWED_EXTENSIONS = {".txt", ".text", ".pdf", ".docx"}
MAX_UPLOAD_BYTES = 25 * 1024 * 1024

class DocumentParseError(ValueError):
    pass

def validate_upload(filename: str, raw: bytes) -> None:
    suffix = Path(filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise DocumentParseError("Only TXT, PDF, and DOCX files are supported")
    if not raw:
        raise DocumentParseError("The uploaded document is empty")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise DocumentParseError("The uploaded document exceeds the 25 MB limit")

def _docx_pages(raw: bytes) -> list[str]:
    try:
        with ZipFile(BytesIO(raw)) as archive:
            xml = archive.read("word/document.xml")
        root = ElementTree.fromstring(xml)
    except Exception as exc:
        raise DocumentParseError("The DOCX document could not be parsed") from exc
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = []
    for node in root.findall(".//w:p", ns):
        text = "".join((part.text or "") for part in node.findall(".//w:t", ns)).strip()
        if text:
            paragraphs.append(text)
    return ["\n\n".join(paragraphs)]

def parse_document(filename: str, raw: bytes) -> list[str]:
    validate_upload(filename, raw)
    suffix = Path(filename).suffix.lower()
    if suffix in {".txt", ".text"}:
        try:
            return raw.decode("utf-8-sig", errors="strict").split("\f")
        except UnicodeDecodeError as exc:
            raise DocumentParseError("The text document is not valid UTF-8") from exc
    if suffix == ".docx":
        return _docx_pages(raw)
    try:
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(raw))
        return [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:
        raise DocumentParseError("The PDF document could not be parsed") from exc
