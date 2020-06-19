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
        "Error in row 3: Duplicate value 'VD-Crotty 1' is not allowed in column 'Antibody name'",
        "Error in row 4: Missing required value in column 'Antibody name'",
        "Error in row 5: Missing required value in column 'Host'",
        "Error in row 6: 'IggA1' is not a valid term in column 'Isotype'",
        "Error in row 7: 'kapa' is not a valid term in column 'Light chain'",
        "Error in row 8: 'IGVH1-8' is not a valid term in column 'Heavy chain germline'",
        "Error in row 9: 'top' is not of type 'integer' in column 'Structural data'",
    ]

    upload = UploadedFile("examples/antibodies-submission-valid.xlsx")
    response = api.validate("antibodies", {"file": upload})
    assert succeeded(response)

    upload = UploadedFile("examples/antibodies-submission-invalid.xlsx")
    response = api.validate("antibodies", {"file": upload})
    assert failed(response)
    assert response["table"][0]["Antibody name"] == "VD-Crotty 1"


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
