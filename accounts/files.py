import os

from django.http import FileResponse, Http404


def serve_pdf_file(resume_field, filename='', inline=False):
    """Return a FileResponse streaming a stored PDF safely with nosniff headers."""
    if not resume_field or not resume_field.storage.exists(resume_field.name):
        raise Http404('Resume file not found.')

    safe_name = os.path.basename(filename or resume_field.name) or 'resume.pdf'
    response = FileResponse(
        resume_field.open('rb'),
        as_attachment=not inline,
        filename=safe_name,
        content_type='application/pdf',
    )
    response['X-Content-Type-Options'] = 'nosniff'
    return response
