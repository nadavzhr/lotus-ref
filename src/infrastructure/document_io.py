"""
Document I/O — read a config file into a Document, write it back.

This is a functional module.  DocumentService will delegate here for
the actual file ↔ Document conversion.

Load flow:
    file → readlines → for each line:
        is_comment?  → DocumentLine(COMMENT)
        is_empty?    → DocumentLine(EMPTY)
        parse(text)  → LineData → validate(data, nqs?) → DocumentLine(DATA)
        ValueError   → DocumentLine(ERROR, errors=[str(e)])

Save flow:
    for each DocumentLine:
        DATA  → serializer.serialize(data)
        other → raw_text as-is
    → write all to file
"""
from __future__ import annotations

import gzip
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from core.document_type import DocumentType
from core.document_line import DocumentLine
from core.document import Document
from core.validation_result import ValidationResult
from core.line_status import LineStatus

import infrastructure.registrations  # noqa: F401  (side-effect: populates the registry)
from infrastructure.registry import get_handler

if TYPE_CHECKING:
    from core.interfaces import INetlistQueryService


# ------------------------------------------------------------------
# File helpers (plain text or gzip)
# ------------------------------------------------------------------

def _is_gz(path: Path) -> bool:
    return path.suffix == ".gz" or path.suffixes[-2:] == [".gz"]


def _read_text(path: Path) -> str:
    if _is_gz(path):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return f.read()
    return path.read_text(encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    if _is_gz(path):
        with gzip.open(path, "wt", encoding="utf-8") as f:
            f.write(content)
    else:
        path.write_text(content, encoding="utf-8")


# ------------------------------------------------------------------
# Parse a single raw text line into a DocumentLine
# ------------------------------------------------------------------

def parse_line(
    raw_text: str,
    doc_type: DocumentType,
    nqs: Optional["INetlistQueryService"] = None,
) -> DocumentLine:
    """
    Convert a single raw text line into a fully classified DocumentLine.

    This is the core building block — used by ``load_document`` during
    initial file load, and by DocumentService when creating or updating
    individual lines.

    The returned DocumentLine carries a ``validation_result`` whose
    ``status`` reflects the line classification:
      COMMENT — handler says it's a comment (e.g. starts with '#')
      ERROR   — could not parse, or parse raised ValueError
      OK / WARNING — successfully parsed; validator may add warnings
    """
    handler = get_handler(doc_type)

    stripped = raw_text.rstrip("\n\r")

    if handler.is_empty(stripped):
        return DocumentLine(
            raw_text=stripped,
            validation_result=ValidationResult(status=LineStatus.OK),
        )

    if handler.is_comment(stripped):
        return DocumentLine(
            raw_text=stripped,
            validation_result=ValidationResult(status=LineStatus.COMMENT),
        )

    try:
        data = handler.parse(stripped)
    except ValueError as exc:
        return DocumentLine(
            raw_text=stripped,
            validation_result=ValidationResult(errors=[str(exc)]),
        )

    # Layer-2 domain validation (+ Layer-3 netlist if nqs provided)
    vr = handler.validate(data, nqs)

    return DocumentLine(
        raw_text=stripped,
        data=data,
        validation_result=vr,
    )


# ------------------------------------------------------------------
# Load
# ------------------------------------------------------------------

def load_document(
    file_path: str | Path,
    doc_type: DocumentType,
    nqs: Optional["INetlistQueryService"] = None,
) -> Document:
    """
    Read a configuration file and return a fully populated Document.

    Every line is parsed, validated, and wrapped in a DocumentLine.
    Lines that fail to parse are preserved as ERROR lines so the
    frontend can display them (with a red indicator) and the user
    can fix them through the edit UI.
    """
    path = Path(file_path)
    raw_lines = _read_text(path).splitlines(keepends=False)

    doc_lines = [parse_line(line, doc_type, nqs) for line in raw_lines]

    return Document(
        doc_type=doc_type,
        file_path=str(path),
        lines=doc_lines,
    )


# ------------------------------------------------------------------
# Save
# ------------------------------------------------------------------

def save_document(
    document: Document,
    file_path: str | Path | None = None,
) -> None:
    """
    Write a Document back to disk.

    For DATA lines the canonical serializer is used so that any edits
    made through the session/controller flow are reflected.  Non-data
    lines (comments, blanks, errors) are written back using their
    original ``raw_text``.
    """
    target = Path(file_path) if file_path else Path(document.file_path)
    if not target:
        raise ValueError("No file path specified and document has no path.")

    serialize = get_handler(document.doc_type).serialize

    output_lines: list[str] = []
    for line in document.lines:
        if line.data is not None:
            output_lines.append(serialize(line.data))
        else:
            output_lines.append(line.raw_text)

    _write_text(target, "\n".join(output_lines) + "\n")
