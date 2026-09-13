class DocumentService:
    """Validaciones estáticas para archivos subidos por el usuario."""

    SUPPORTED_TYPES = {"pdf", "docx", "txt"}
    MAX_SIZE_MB = 10

    @staticmethod
    def validate_file_type(file_extension: str) -> bool:
        return file_extension.lower() in DocumentService.SUPPORTED_TYPES

    @staticmethod
    def validate_file_size(file_size: int, max_size_mb: int = MAX_SIZE_MB) -> bool:
        return file_size <= max_size_mb * 1024 * 1024
