from dataclasses import dataclass, field

from core.line_status import LineStatus


@dataclass(slots=True)
class ValidationResult:
    """
    Outcome of validating a document line.

    ``status`` is a stored field whose default is ``OK``.
    ``__post_init__`` auto-promotes it to ``ERROR`` or ``WARNING``
    when errors or warnings are present at construction time.

    For non-data lines (comments, blanks) ``parse_line`` passes the
    desired status explicitly — since no errors/warnings are set,
    ``__post_init__`` leaves it untouched.
    """
    status: LineStatus = LineStatus.OK
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.errors:
            self.status = LineStatus.ERROR
        elif self.warnings:
            self.status = LineStatus.WARNING

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def __bool__(self) -> bool:
        return self.is_valid
