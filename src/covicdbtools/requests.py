import os

from datetime import datetime


def validate(submitter_id, submitter_label, request_files):
    """Given a submitted_id string, a submitter_label string,
    and Django request.FILES object with one file,
    store it in a temporary file, validate it, and return a response dictionary."""
    if len(request_files.keys()) > 1:
        return {"status": 400, "message": "Multiple upload files not allowed"}

    datestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")  # 20200322-084530-123456
    temp = os.path.join("temp", datestamp)
    try:
        os.makedirs(temp)
    except Exception as e:
        return {
            "status": 400,
            "message": "Could not create temp directory",
            "exception": e,
        }

    path = None
    try:
        for upload_file in request_files.values():
            path = os.path.join(temp, upload_file.name)
            with open(path, "wb+") as f:
                for chunk in upload_file.chunks():
                    f.write(chunk)
    except Exception as e:
        return {"status": 400, "message": "Invalid upload", "exception": e}
