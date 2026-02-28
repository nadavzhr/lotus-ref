from __future__ import annotations



class MutexSessionError(Exception):
    """Base class for all mutex session errors."""


class DuplicateEntryError(MutexSessionError):
    """Raised when attempting to add a duplicate entry."""


class TemplateMismatchError(MutexSessionError):
    """Raised when an entry's template does not match session template."""


class RegexModeMismatchError(MutexSessionError):
    """Raised when an entry's regex mode does not match session mode."""


class IntersectionError(MutexSessionError):
    """Raised when an entry intersects with existing entries."""


class ActiveRegexError(MutexSessionError):
    """Raised when trying to add a regex entry to the active set."""


class ActiveMultipleMatchesError(MutexSessionError):
    """Raised when trying to add an entry that resolves to multiple nets to the active set."""


class NoMatchesError(MutexSessionError):
    """Raised when an entry does not resolve to any nets."""


class EntryNotFoundError(MutexSessionError):
    """Raised when trying to remove an entry that is not present."""

class ValidationError(MutexSessionError):
    """Raised when validation of the session state fails."""

class InvalidFEVModeError(MutexSessionError):
    """Raised when an invalid FEV mode is set."""


