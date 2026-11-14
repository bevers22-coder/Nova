import unittest
from io import BytesIO
from zipfile import ZipFile

from modules.document_tools import export_document


class DocumentExportTests(unittest.TestCase):
    def test_text_formats_contain_the_authored_content(self):
        markdown, name, mime = export_document("Study Guide", "# Cells\nMitochondria", "Markdown")
        self.assertEqual(name, "Study-Guide.md")
        self.assertEqual(mime, "text/markdown")
        self.assertIn(b"Mitochondria", markdown)
        text, _, _ = export_document("Study Guide", "# Cells\nMitochondria", "Plain text")
        self.assertIn(b"Cells", text)
        self.assertNotIn(b"# Cells", text)

    def test_docx_and_pdf_are_valid_download_payloads(self):
        docx, _, _ = export_document("Research", "# Findings\nEvidence matters.", "Word document")
        with ZipFile(BytesIO(docx)) as package:
            self.assertIn("word/document.xml", package.namelist())
            self.assertIn(b"Evidence matters", package.read("word/document.xml"))
        pdf, _, mime = export_document("Research", "# Findings\nEvidence matters.", "PDF")
        self.assertEqual(mime, "application/pdf")
        self.assertTrue(pdf.startswith(b"%PDF-"))

    def test_empty_content_and_unsupported_formats_are_rejected(self):
        with self.assertRaises(ValueError):
            export_document("Empty", " ", "PDF")
        with self.assertRaises(ValueError):
            export_document("Test", "content", "CSV")


if __name__ == "__main__":
    unittest.main()
