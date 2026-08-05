import io
import pytest
from pypdf import PdfWriter
from followup_agent import pdf


def _make_pdf(lines: list[str]) -> bytes:
    """Build a minimal one-page PDF whose text layer contains `lines`.

    Hand-assembled rather than generated with a layout library so the tests
    need no extra dependency. The xref offsets have to be byte-exact, so they
    are measured from the assembled output instead of hard-coded.
    """
    content = "BT /F1 12 Tf 72 720 Td 14 TL\n"
    for line in lines:
        escaped = line.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
        content += f"({escaped}) Tj T*\n"
    content += "ET"
    stream = content.encode("latin-1")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n"
        + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"

    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_at}\n%%EOF\n").encode()
    return bytes(out)


RESUME_LINES = [
    "Jane Chen",
    "jane.chen@example.com  ·  Sydney, Australia",
    "EXPERIENCE",
    "Senior Engineer, Acme Corp, 2023-2026",
    "Built the billing pipeline handling 2M events a day.",
    "EDUCATION",
    "BSc Computer Science, UNSW, 2022",
]


def test_extracts_text_from_a_pdf():
    text = pdf.extract_text(_make_pdf(RESUME_LINES))
    assert "Jane Chen" in text
    assert "jane.chen@example.com" in text
    assert "UNSW" in text


def test_collapses_runs_of_whitespace():
    text = pdf.extract_text(_make_pdf(RESUME_LINES))
    assert "  " not in text
    assert "\n\n\n" not in text


def test_page_without_a_text_layer_raises():
    # A structurally valid PDF whose only page draws no text — what a scan
    # looks like to a parser.
    with pytest.raises(pdf.NoTextLayerError):
        pdf.extract_text(_make_pdf([]))


def test_encrypted_pdf_raises():
    writer = PdfWriter(clone_from=io.BytesIO(_make_pdf(RESUME_LINES)))
    writer.encrypt("hunter2")
    buf = io.BytesIO()
    writer.write(buf)
    with pytest.raises(pdf.EncryptedPdfError):
        pdf.extract_text(buf.getvalue())


def test_bytes_that_are_not_a_pdf_raise():
    with pytest.raises(pdf.UnreadablePdfError):
        pdf.extract_text(b"this is a plain text file, not a PDF")


def test_every_failure_shares_one_base_class():
    # Task 5 relies on being able to catch pdf.PdfError as a backstop.
    for exc in (pdf.EncryptedPdfError, pdf.NoTextLayerError, pdf.UnreadablePdfError):
        assert issubclass(exc, pdf.PdfError)
