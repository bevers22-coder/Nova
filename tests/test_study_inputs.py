import base64
import unittest
from io import BytesIO

from docx import Document

from modules.study_inputs import read_study_upload


class StudyInputTests(unittest.TestCase):
    def test_reads_text_and_docx_uploads(self):
        text, image = read_study_upload("notes.txt", b"Cell structure")
        self.assertEqual(text, "Cell structure")
        self.assertIsNone(image)

        document = Document()
        document.add_paragraph("Photosynthesis")
        output = BytesIO()
        document.save(output)
        text, image = read_study_upload("biology.docx", output.getvalue())
        self.assertIn("Photosynthesis", text)
        self.assertIsNone(image)

    def test_images_become_inline_data_uris(self):
        text, data_uri = read_study_upload("assignment.png", b"image bytes")
        self.assertEqual(text, "")
        self.assertTrue(data_uri.startswith("data:image/png;base64,"))
        self.assertEqual(base64.b64decode(data_uri.split(",", 1)[1]), b"image bytes")

    def test_rejects_unsupported_and_oversized_uploads(self):
        with self.assertRaises(ValueError):
            read_study_upload("archive.zip", b"data")
        with self.assertRaises(ValueError):
            read_study_upload("large.txt", b"x" * (8 * 1024 * 1024 + 1))


if __name__ == "__main__":
    unittest.main()
