"""Load Markdown sections while keeping their original source locations."""
import re
from pathlib import Path
from .models import Passage


def load_passages(folder: Path) -> list[Passage]:
    if not folder.is_dir():
        raise ValueError(f"SOP directory does not exist: {folder}")
    passages = []
    for path in sorted(folder.glob("*.md")):
        lines = path.read_text(encoding="utf-8").splitlines()
        title = next((line[2:].strip() for line in lines if line.startswith("# ")),
                     path.stem)
        section = "Introduction"
        start = 0
        for index, line in enumerate(lines + ["## END"]):
            heading = re.match(r"^#{1,6}\s+(.+)$", line)
            if heading:
                body = "\n".join(lines[start:index])
                if body.strip():
                    passages.append(Passage(title, path.as_posix(), section,
                                            start + 1, index, body))
                section = heading.group(1)
                start = index + 1
    return passages
