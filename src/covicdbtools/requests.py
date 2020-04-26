from io import BytesIO
from covicdbtools.responses import success, failure, xlsx


def is_request(request_files):
    return hasattr(request_files, "file") or "file" in request_files


def read_file(request_files):
    """Given a submitted_id string, a submitter_label string,
    and Django request.FILES object with one file,
    return a request object with a "filename" string and a "bytes" BytesIO."""
    if len(request_files.keys()) < 1:
        return failure("No files in request")
    if len(request_files.keys()) > 1:
        return failure("Multiple upload files not allowed")

    upload_file = list(request_files.values())[0]
    filename = upload_file.name
    if not filename.endswith(".xlsx"):
        return failure("Only .xlsx files are supported at this time.")
    content = BytesIO()
    try:
        for chunk in upload_file.chunks():
            content.write(chunk)
    except Exception as e:
        return failure("Invalid upload", {"exception": e})

    return success({"filename": filename, "content type": xlsx, "content": content})
