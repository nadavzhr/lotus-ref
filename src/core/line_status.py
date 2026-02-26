from enum import Enum


class LineStatus(Enum):
    """
    Validation / health state of a document line — drives frontend coloring.
    """
    OK = "ok"              # valid data, no errors, no warnings
    WARNING = "warning"    # valid but has warnings (e.g. non-canonical net name)
    ERROR = "error"        # has validation or parse errors
    COMMENT = "comment"    # line is a comment (starts with #)
    CONFLICT = "conflict"  # reserved — will indicate merge / edit conflicts
