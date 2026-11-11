from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile

MAX_RESUME_BYTES = 5 * 1024 * 1024


def validate_pdf_resume(uploaded_file):
    """Validate that an uploaded resume is a real PDF document within 5 MB."""
    if not isinstance(uploaded_file, UploadedFile):
        return uploaded_file

    if not uploaded_file.name.lower().endswith('.pdf'):
        raise ValidationError('Only PDF files (.pdf) are allowed.')

    if uploaded_file.size > MAX_RESUME_BYTES:
        raise ValidationError('Resume file size must not exceed 5 MB.')

    header = uploaded_file.read(5)
    uploaded_file.seek(0)
    if header != b'%PDF-':
        raise ValidationError('The uploaded file is not a valid PDF document.')

    return uploaded_file
