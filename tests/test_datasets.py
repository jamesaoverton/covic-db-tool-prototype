from covicdbtools import tables, workbooks, datasets, api
from covicdbtools.responses import succeeded, failed
from .test_requests import UploadedFile


def test_get_assay_header():
    header, error = datasets.get_assay_header("foo")
    assert not header and error, "'foo' is not an assay"

    header, error = datasets.get_assay_header("obi_0001643")
    assert header and not error, "OBI:0001643 'neutralization' is an assay"

    header, error = datasets.get_assay_header("ontie_0003576")
    assert header and not error, "ONTIE:0003576 'Starting dilution fold' is a paramter"


def test_validate_submission():
    path = "examples/spr-submission-valid.xlsx"
    table = workbooks.read(path, "Dataset")
    response = datasets.validate("spr", table)
    assert succeeded(response)

    path = "examples/spr-submission-invalid.xlsx"
    table = workbooks.read(path, "Dataset")
    response = datasets.validate("spr", table)
    assert failed(response)
    assert response["errors"] == [
        "Error in row 2: 'COVIC 1' is not a valid COVIC antibody label "
        + "or control antibody label in column 'Antibody label'",
        "Error in row 2: 'X' is not of type 'non-negative integer' in column 'n'",
        "Error in row 2: '7000O' is not of type 'float_threshold_na'"
        " in column 'Standard deviation in M^-1s^-1'",
        "Error in row 2: 'Positive' is not a valid term in column 'Qualitiative measure'",
    ]

    upload = UploadedFile("examples/spr-submission-valid.xlsx")
    response = api.validate("spr", {"file": upload})
    assert succeeded(response)

    upload = UploadedFile("examples/spr-submission-invalid.xlsx")
    response = api.validate("spr", {"file": upload})
    assert failed(response)
    assert response["table"][0]["Antibody label"] == "COVIC 1"


def test_examples():
    examples = ["spr-submission"]
    for example in examples:
        table = []
        excel = workbooks.read("examples/{0}.xlsx".format(example))
        assert table == excel

    examples = [
        "spr-submission-valid",
        "spr-submission-invalid",
    ]
    for example in examples:
        tsv = tables.read_tsv("examples/{0}.tsv".format(example))
        excel = workbooks.read("examples/{0}.xlsx".format(example))
        assert tables.table_to_lists(tsv)[1:] == tables.table_to_lists(excel)[1:]
