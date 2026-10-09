"""Local upload storage with validated filenames and no silent overwrites."""
import re
from pathlib import Path
from tempfile import TemporaryDirectory
from .loader import parse_document

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
SUPPORTED = {".md", ".pdf", ".docx"}


class DocumentCollection:
    def __init__(self, directory: Path):
        self.directory = directory.resolve()
        self.directory.mkdir(parents=True, exist_ok=True)

    def list_documents(self) -> list[Path]:
        return sorted(p for p in self.directory.iterdir()
                      if p.is_file() and not p.is_symlink() and p.suffix.lower() in SUPPORTED)

    def _path(self, name: str) -> Path:
        # Restrict names rather than rewriting them: avoids collisions and traversal.
        if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._-]{0,119}", name)
                or name.endswith((" ", "."))
                or Path(name).suffix.lower() not in SUPPORTED
                or name.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL",
                    *[f"COM{i}" for i in range(1, 10)], *[f"LPT{i}" for i in range(1, 10)]}):
            raise ValueError("Use a simple filename (letters, numbers, spaces, dots, underscores or hyphens) with .md, .pdf or .docx.")
        path = self.directory / name
        if path.is_symlink() or path.resolve().parent != self.directory:
            raise ValueError("Invalid document path.")
        return path

    def add(self, name: str, content: bytes) -> Path:
        destination = self._path(name)
        if not content or len(content) > MAX_UPLOAD_BYTES:
            raise ValueError("Upload must contain data and be no larger than 20 MB.")
        if destination.exists():
            raise ValueError("A document with this name already exists. Remove it first or rename the upload.")
        # Parse before persisting; rejected uploads leave no collection entry.
        with TemporaryDirectory(dir=self.directory) as temporary:
            candidate = Path(temporary) / name
            candidate.write_bytes(content)
            parse_document(candidate)
            with destination.open("xb") as output:
                output.write(content)
        return destination

    def remove(self, name: str) -> None:
        path = self._path(name)
        if not path.is_file():
            raise ValueError("Document is no longer in the collection.")
        path.unlink()

    def load(self):
        passages, errors = [], []
        for path in self.list_documents():
            try:
                passages.extend(parse_document(path))
            except ValueError as error:
                errors.append((path.name, str(error)))
        return passages, errors
