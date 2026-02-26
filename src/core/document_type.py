from enum import Enum


class DocumentType(Enum):
    """Determines which parser / validator / serializer family to use."""
    AF = "af"
    MUTEX = "mutex"
