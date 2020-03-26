import os

from covicdbtools import datasets, workbooks
from .test_requests import UploadedFile


def test_validate_request():
    upload = UploadedFile("examples/neutralization-submission.xlsx")
    result = datasets.validate_request("OBI:0001643", {"file": upload})
    assert result == {"status": 200, "message": "Success", "table": []}

    upload = UploadedFile("examples/neutralization-submission-invalid.xlsx")
    result = datasets.validate_request("OBI:0001643", {"file": upload})
    assert result["status"] == 400
    table = workbooks.read_xlsx(result["content"], "Dataset")
    assert table[0]["Antibody name"] == "COVIC 1"
