"""Turning an uploaded PDF into plain text.

The client's declared content type is a hint, not a fact — the bytes are
parsed here and rejected if they are not a readable, text-bearing PDF.
"""
import io
import re

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class PdfError(Exception):
    """Base for every reason a PDF could not be turned into text."""


class EncryptedPdfError(PdfError):
    """Password-protected, and the empty password did not open it."""


class NoTextLayerError(PdfError):
    """Parsed fine but carries no text — almost always a scanned image."""


class UnreadablePdfError(PdfError):
    """Not a PDF, or structurally corrupt."""


# Anything shorter than this is page furniture (a header, a page number),
# not a résumé. Chosen low enough that a genuinely terse résumé still passes.
_MIN_CHARS = 50


def extract_text(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
    except (PdfReadError, OSError, ValueError) as e:
        raise UnreadablePdfError(str(e)) from e

    if reader.is_encrypted:
        # An empty user password is common on documents exported with
        # print/copy restrictions, and those are perfectly readable. Try it
        # before rejecting the file.
        try:
            opened = reader.decrypt("")
        except (NotImplementedError, PdfReadError) as e:
            raise EncryptedPdfError(str(e)) from e
        if not opened:
            raise EncryptedPdfError("password-protected")

    try:
        pages = [page.extract_text() or "" for page in reader.pages]
    except (PdfReadError, ValueError) as e:
        raise UnreadablePdfError(str(e)) from e

    text = _normalise("\n".join(pages))
    if len(text) < _MIN_CHARS:
        raise NoTextLayerError("no extractable text")
    return text


def _normalise(text: str) -> str:
    """PDF text extraction emits ragged spacing; the LLM reads better without it."""
    text = text.replace("\r\n", "\n").replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return "\n".join(line.strip() for line in text.split("\n")).strip()
