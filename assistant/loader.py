"""Load Markdown sections while keeping their original source locations."""
import re
from pathlib import Path
from .models import Passage


class DocumentParseError(ValueError):
    """Safe, user-facing parsing failure."""


def load_passages(folder: Path) -> list[Passage]:
    if not folder.is_dir():
        raise ValueError(f"SOP directory does not exist: {folder}")
    passages = []
    for path in sorted(folder.glob("*.md")):
        passages.extend(parse_document(path))
    return passages


def parse_document(path: Path) -> list[Passage]:
    """Read one supported document. PDF requires text (no OCR)."""
    suffix = path.suffix.lower()
    try:
        if suffix == ".md":
            return parse_markdown(path)
        if suffix == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(path)
            if reader.is_encrypted:
                raise DocumentParseError("Encrypted PDFs are not supported.")
            passages = []
            for number, page in enumerate(reader.pages, 1):
                text = (page.extract_text() or "").strip()
                if text:
                    passages.append(Passage(path.stem, path.as_posix(), f"Page {number}",
                                            1, len(text.splitlines()), text, number, "extracted lines"))
        elif suffix == ".docx":
            from docx import Document
            document = Document(path)
            passages = []
            section = "Introduction"
            buffer = []
            start = 1
            # iter_inner_content preserves paragraph/table order (python-docx 1.2+).
            from docx.table import Table
            blocks = list(document.iter_inner_content())
            for number, block in enumerate(blocks, 1):
                if isinstance(block, Table):
                    text = "\n".join(" | ".join(cell.text for cell in row.cells)
                                     for row in block.rows)
                    is_heading = False
                else:
                    text = block.text
                    is_heading = block.style.name.startswith("Heading")
                if is_heading:
                    if "\n".join(buffer).strip():
                        passages.append(Passage(path.stem, path.as_posix(), section, start,
                                                number - 1, "\n".join(buffer), location_kind="blocks"))
                    section, buffer, start = text, [], number + 1
                else:
                    buffer.append(text)
            if "\n".join(buffer).strip():
                passages.append(Passage(path.stem, path.as_posix(), section, start,
                                        len(blocks), "\n".join(buffer), location_kind="blocks"))
        else:
            raise DocumentParseError("Supported formats are Markdown (.md), PDF, and DOCX.")
        if not passages:
            raise DocumentParseError("No readable text found. Scanned PDFs require OCR, which is not included.")
        return passages
    except ImportError:
        raise DocumentParseError("Document parser is missing. Install requirements.txt.") from None
    except DocumentParseError:
        raise
    except Exception:
        # Parser exceptions may include document text; expose only a safe message.
        raise DocumentParseError("Document could not be parsed. Check its format and whether it is damaged.") from None


def parse_markdown(path: Path) -> list[Passage]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    title = next((line[2:].strip() for line in lines if line.startswith("# ")),
                 path.stem)
    section = "Introduction"
    start = 0
    passages = []
    for index, line in enumerate(lines + ["## END"]):
        heading = re.match(r"^#{1,6}\s+(.+)$", line)
        if heading:
            body = "\n".join(lines[start:index])
            if body.strip():
                passages.append(Passage(title, path.as_posix(), section,
                                        start + 1, index, body))
            section = heading.group(1)
            start = index + 1
    if not passages:
        raise DocumentParseError("No readable text found in Markdown document.")
    return passages
