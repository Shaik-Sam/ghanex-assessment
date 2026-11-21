class RagError(Exception):
    pass


class UnsupportedFormatError(RagError):
    pass


class EncryptedDocumentError(RagError):
    pass


class EmptyDocumentError(RagError):
    pass


class CorruptDocumentError(RagError):
    pass


class FileTooLargeError(RagError):
    pass


class GenerationError(RagError):
    pass


class NoDocumentsError(RagError):
    pass
