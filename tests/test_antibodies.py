import os

from collections import OrderedDict

from covicdbtools import tables, workbooks, antibodies, api
from covicdbtools.responses import succeeded, failed
from .test_requests import UploadedFile


def test_validate():
    path = "examples/antibodies-submission-valid.tsv"
    table = tables.read_tsv(path)
    response = antibodies.validate(table)
    assert succeeded(response)

    path = "examples/antibodies-submission-invalid.tsv"
    table = tables.read_tsv(path)
    response = antibodies.validate(table)
    assert failed(response)
    assert response["errors"] == [
        "Error in row 3: Missing required value for 'Antibody name'",
        "Error in row 6: Missing required value for 'Host'",
        "Error in row 6: 'Ig1' is not a recognized value for 'Isotype'",
        "Error in row 8: 'Mus musclus' is not a recognized value for 'Host'",
        "Error in row 8: 'Igm' is not a recognized value for 'Isotype'",
        "Error in row 9: Duplicate value 'C3' is not allowed for 'Antibody name'",
    ]

    upload = UploadedFile("examples/antibodies-submission-valid.xlsx")
    response = api.validate("antibodies", {"file": upload})
    assert succeeded(response)

    upload = UploadedFile("examples/antibodies-submission-invalid.xlsx")
    response = api.validate("antibodies", {"file": upload})
    assert failed(response)
    assert response["table"][0]["Antibody name"] == "A6"


def test_examples():
    example = "antibodies-submission"
    table = []
    excel = workbooks.read("examples/{0}.xlsx".format(example))
    assert table == excel

    examples = ["antibodies-submission-valid", "antibodies-submission-invalid"]
    for example in examples:
        tsv = tables.read_tsv("examples/{0}.tsv".format(example))
        excel = workbooks.read("examples/{0}.xlsx".format(example))
        assert tsv == excel

    example = "antibodies-submission-invalid"
    tsv = tables.read_tsv("examples/{0}.tsv".format(example))
    example = "antibodies-submission-invalid-highlighted"
    excel = workbooks.read("examples/{0}.xlsx".format(example))
    assert tsv == excel
