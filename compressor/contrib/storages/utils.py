from django.core.files import File

try:
    from io import BytesIO as StringIO
except ImportError:
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO


def create_content_copy(content):
    """
    Create a safe copy of file content that won't be affected by operations on the original.

    Handles both File objects with a .file attribute and ContentFile objects which don't have one.

    Args:
        content: A file-like object (File, ContentFile, etc.)

    Returns:
        A new File object with the same content
    """
    content_copy = content

    if hasattr(content, 'file'):
        # Handle File objects with a .file attribute
        if hasattr(content.file, 'seek'):
            original_pos = content.file.tell()
            content.file.seek(0)
            file_content = content.file.read()
            content_copy = File(StringIO(file_content))
            # Reset pointer of original content
            content.file.seek(original_pos)
    elif hasattr(content, 'seek'):
        # Handle ContentFile objects without a .file attribute
        original_pos = content.tell()
        content.seek(0)
        file_content = content.read()
        content_copy = File(StringIO(file_content))
        # Reset to original position
        content.seek(original_pos)

    return content_copy
