import os

from collections import OrderedDict

from covicdbtools import config, tables, workbooks, datasets, api
from covicdbtools.responses import succeeded, failed
from .test_requests import UploadedFile

config.ids = {
    "neutralization": "OBI:0001643",
    "VLP ELISA": "OBI:0000661",
}


def test_validate_submission():
    path = "examples/neutralization-submission-valid.tsv"
    table = tables.read_tsv(path)
    response = datasets.validate("neutralization", table)
    assert succeeded(response)

    path = "examples/neutralization-submission-invalid.tsv"
    table = tables.read_tsv(path)
    response = datasets.validate("neutralization", table)
    assert failed(response)
    assert response["errors"] == [
        "Error in row 2: Missing required value for 'Antibody name'",
        "Error in row 3: Duplicate value 'COVIC 1' is not allowed for 'Antibody name'",
        "Error in row 5: 'postive' is not a recognized value for 'Qualitative measure'",
        "Error in row 5: 'none' is not of type 'float' in 'Titer'",
        "Error in row 6: 'intermediate' is not a recognized value for 'Qualitative measure'",
    ]

    path = "examples/VLP-ELISA-submission-valid.tsv"
    table = tables.read_tsv(path)
    response = datasets.validate("VLP ELISA", table)
    assert succeeded(response)


def test_validate_request():
    upload = UploadedFile("examples/neutralization-submission.xlsx")
    response = api.validate_request("neutralization", {"file": upload})
    assert succeeded(response)

    upload = UploadedFile("examples/neutralization-submission-invalid.xlsx")
    response = api.validate_request("neutralization", {"file": upload})
    assert failed(response)
    assert response["table"][0]["Antibody name"] == "COVIC 1"


def test_examples():
    examples = ["neutralization-submission", "VLP-ELISA-submission"]
    for example in examples:
        table = []
        excel = workbooks.read("examples/{0}.xlsx".format(example))
        assert table == excel

    examples = [
        "neutralization-submission-valid",
        "neutralization-submission-invalid",
        "VLP-ELISA-submission-valid",
    ]
    for example in examples:
        tsv = tables.read_tsv("examples/{0}.tsv".format(example))
        excel = workbooks.read("examples/{0}.xlsx".format(example))
        assert tsv == excel

    example = "neutralization-submission-invalid"
    tsv = tables.read_tsv("examples/{0}.tsv".format(example))
    example = "neutralization-submission-invalid-highlighted"
    excel = workbooks.read("examples/{0}.xlsx".format(example))
    assert tsv == excel
