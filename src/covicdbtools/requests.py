import os

from io import BytesIO


def read_file(request_files):
    """Given a submitted_id string, a submitter_label string,
    and Django request.FILES object with one file,
    return a request object with a "filename" string and a "bytes" BytesIO."""
    if len(request_files.keys()) < 1:
        return {"status": 400, "message": "No files in request"}
    if len(request_files.keys()) > 1:
        return {"status": 400, "message": "Multiple upload files not allowed"}

    upload_file = list(request_files.values())[0]
    content = BytesIO()
    try:
        for chunk in upload_file.chunks():
            content.write(chunk)
    except Exception as e:
        return {"status": 400, "message": "Invalid upload", "exception": e}

    return {"status": 200, "filename": upload_file.name, "content": content}
