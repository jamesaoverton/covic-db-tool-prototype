import os

from covicdbtools import antibodies, workbooks
from .test_requests import UploadedFile


def test_validate_request():
    upload = UploadedFile("examples/antibodies-submission.xlsx")
    result = antibodies.validate_request("org:1", "Acme", {"file": upload})
    assert result == {"status": 200, "message": "Success", "table": []}

    upload = UploadedFile("examples/antibodies-submission-invalid.xlsx")
    result = antibodies.validate_request("org:1", "Acme", {"file": upload})
    assert result["status"] == 400
    table = workbooks.read_xlsx(result["content"], "Antibodies")
    assert table[0]["Antibody name"] == "A6"
