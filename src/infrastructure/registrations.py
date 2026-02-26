"""
Central wiring — register all document type handlers.

To add a new document type, add one ``register()`` call below.
This module is imported (as a side-effect) by ``document_io``
to ensure handlers are available before first use.
"""
from core.document_type import DocumentType
from infrastructure.registry import register, DocumentTypeHandler

from doc_types.af import parser as af_parser

from doc_types.mutex import parser as mutex_parser
from doc_types.af import serializer as af_serializer
from doc_types.mutex import serializer as mutex_serializer
from doc_types.af.validator import validate_af
from doc_types.mutex.validator import validate_mutex


# ---- AF ----
register(DocumentType.AF, DocumentTypeHandler(
    is_comment=af_parser.is_comment,
    is_empty=af_parser.is_empty,
    parse=af_parser.parse,
    serialize=af_serializer.serialize,
    validate=validate_af,
))

# ---- Mutex ----
register(DocumentType.MUTEX, DocumentTypeHandler(
    is_comment=mutex_parser.is_comment,
    is_empty=mutex_parser.is_empty,
    parse=mutex_parser.parse,
    serialize=mutex_serializer.serialize,
    validate=validate_mutex,
))
