import os

from collections import OrderedDict

from covicdbtools import config, tables, workbooks, datasets
from .test_requests import UploadedFile

config.labels = {
    "OBI:0001643": "neutralization",
    "OBI:0000661": "VLP ELISA",
}


def test_validate_submission():
    path = "examples/neutralization-submission-valid.tsv"
    table = tables.read_tsv(path)
    grid = datasets.validate_submission("OBI:0001643", table)
    assert grid is None

    path = "examples/neutralization-submission-invalid.tsv"
    table = tables.read_tsv(path)
    grid = datasets.validate_submission("OBI:0001643", table)
    errors = grid["errors"]
    assert errors == [
        "Error in row 2: Missing required value for 'Antibody name'",
        "Error in row 3: Duplicate value 'COVIC 1' is not allowed for 'Antibody name'",
        "Error in row 5: 'postive' is not a recognized value for 'Qualitative measure'",
        "Error in row 5: 'none' is not of type 'float' in 'Titer'",
        "Error in row 6: 'intermediate' is not a recognized value for 'Qualitative measure'",
    ]

    path = "examples/VLP-ELISA-submission-valid.tsv"
    table = tables.read_tsv(path)
    grid = datasets.validate_submission("OBI:0000661", table)
    assert grid is None


def test_validate_request():
    upload = UploadedFile("examples/neutralization-submission.xlsx")
    result = datasets.validate_request("OBI:0001643", {"file": upload})
    assert result == {"status": 200, "message": "Success", "table": []}

    upload = UploadedFile("examples/neutralization-submission-invalid.xlsx")
    result = datasets.validate_request("OBI:0001643", {"file": upload})
    assert result["status"] == 400
    table = workbooks.read_xlsx(result["content"], "Dataset")
    assert table[0]["Antibody name"] == "COVIC 1"


def test_examples():
    examples = ["neutralization-submission", "VLP-ELISA-submission"]
    for example in examples:
        table = []
        excel = workbooks.read_xlsx("examples/{0}.xlsx".format(example))
        assert table == excel

    examples = [
        "neutralization-submission-valid",
        "neutralization-submission-invalid",
        "VLP-ELISA-submission-valid",
    ]
    for example in examples:
        tsv = tables.read_tsv("examples/{0}.tsv".format(example))
        excel = workbooks.read_xlsx("examples/{0}.xlsx".format(example))
        assert tsv == excel

    example = "neutralization-submission-invalid"
    tsv = tables.read_tsv("examples/{0}.tsv".format(example))
    example = "neutralization-submission-invalid-highlighted"
    excel = workbooks.read_xlsx("examples/{0}.xlsx".format(example))
    assert tsv == excel
