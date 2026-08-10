"""
rag/parser/validator.py
Security validation for file uploads (MIME checking, path traversal protection, Zip-bomb detection).
"""
import os
import zipfile
from typing import Tuple
from werkzeug.utils import secure_filename

ALLOWED_MIME_TYPES = {
    "pdf": ["application/pdf"],
    "docx": ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/zip"],
    "xlsx": ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/zip"],
    "xls": ["application/vnd.ms-excel"],
    "txt": ["text/plain"],
    "md": ["text/plain", "text/markdown"],
}

# Maximum uncompressed size for zip-based files (DOCX/XLSX) to prevent Zip Bombs (50 MB)
MAX_UNCOMPRESSED_SIZE = 50 * 1024 * 1024
# Maximum compression ratio allowed
MAX_COMPRESSION_RATIO = 100


def validate_file_header(file_stream, ext: str) -> bool:
    """Validate file magic numbers / magic header bytes."""
    header = file_stream.read(8)
    file_stream.seek(0)
    
    if ext == "pdf":
        return header.startswith(b"%PDF-")
    elif ext in ("docx", "xlsx"):
        # Office Open XML files are ZIP archives starting with PK\x03\x04
        return header.startswith(b"PK\x03\x04")
    elif ext == "xls":
        # Legacy Compound Binary Format (OLE2)
        return header.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1") or header.startswith(b"PK\x03\x04")
    return True


def inspect_zip_bomb(file_path: str) -> Tuple[bool, str]:
    """
    Inspect DOCX / XLSX zip archives to detect potential Zip Bombs before parsing.
    Checks compression ratio and cumulative uncompressed size.
    """
    try:
        if not zipfile.is_zipfile(file_path):
            return False, "File is not a valid zip archive."
            
        total_uncompressed = 0
        total_compressed = 0

        with zipfile.ZipFile(file_path, "r") as zf:
            for info in zf.infolist():
                total_uncompressed += info.file_size
                total_compressed += info.compress_size
                
                if total_uncompressed > MAX_UNCOMPRESSED_SIZE:
                    return False, f"File exceeds maximum uncompressed size limit ({MAX_UNCOMPRESSED_SIZE // (1024*1024)}MB)."

            if total_compressed > 0:
                ratio = total_uncompressed / total_compressed
                if ratio > MAX_COMPRESSION_RATIO:
                    return False, f"Potential Zip-Bomb detected (Compression ratio {ratio:.1f}x exceeds limit)."
                    
        return True, ""
    except Exception as e:
        return False, f"Zip inspection failed: {str(e)}"


def sanitize_and_validate_upload(
    file_storage,
    allowed_extensions: set,
    max_size_bytes: int = 32 * 1024 * 1024
) -> Tuple[bool, str, str]:
    """
    Full security validation for file uploads:
    - Path traversal neutralization
    - Extension & size validation
    - Magic header check
    - Zip-bomb inspection for DOCX/XLSX
    
    Returns: (is_valid, safe_filename, error_message)
    """
    if not file_storage or not file_storage.filename:
        return False, "", "No file selected."

    # 1. Neutralize Path Traversal
    raw_filename = os.path.basename(file_storage.filename)
    safe_name = secure_filename(raw_filename)
    if not safe_name:
        return False, "", "Invalid filename."

    ext = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""
    if ext not in allowed_extensions:
        return False, "", f"File type '.{ext}' is not permitted."

    # 2. File size check
    file_storage.seek(0, os.SEEK_END)
    size = file_storage.tell()
    file_storage.seek(0)

    if size == 0:
        return False, "", "File is empty."
    if size > max_size_bytes:
        return False, "", f"File exceeds maximum allowed size ({max_size_bytes // (1024*1024)}MB)."

    # 3. Magic header check
    if not validate_file_header(file_storage, ext):
        return False, "", f"File content does not match expected format for .{ext} file."

    return True, safe_name, ""
