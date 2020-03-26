#!/usr/bin/env python3

import argparse
import os
import yaml

from collections import OrderedDict
from copy import deepcopy
from io import BytesIO

from covicdbtools import (
    names,
    tables,
    grids,
    workbooks,
    templates,
    requests,
    responses,
    submissions,
)

### Hardcoded fields
# TODO: Make this configurable

assays_table = tables.read_tsv("ontology/assays.tsv")
assays = [r["label"] for r in assays_table[1:]]

qualitative_measures = ["positive", "negative", "unknown"]

headers = {
    "ab_label": {
        "value": "ab_label",
        "label": "Antibody name",
        "description": "The antibody's CoVIC ID.",
        "locked": True,
        "required": True,
        "unique": True,
    },
    "qualitative_measure": {
        "value": "qualitative_measure",
        "label": "Qualitative measure",
        "description": "The qualitative assay result.",
        "locked": True,
        "terminology": qualitative_measures,
        "validations": [
            {
                "type": "list",
                "formula1": "=Terminology!$A$2:$A${0}".format(
                    len(qualitative_measures) + 1
                ),
                "allow_blank": True,
            }
        ],
    },
    "titer": {
        "value": "titer",
        "label": "Titer",
        "description": "The concentration",
        "locked": True,
        "required": True,
        "type": "float",
    },
    "comment": {
        "value": "comment",
        "label": "Comment",
        "description": "A free-text comment on the assay",
        "locked": True,
    },
}

assay_type_labels = {
    "OBI:0001643": "neutralization",
    "OBI:0000661": "VLP ELISA",
}

assay_types = {
    "OBI:0001643": ["ab_label", "qualitative_measure", "titer"],
    "OBI:0000661": ["ab_label", "qualitative_measure", "comment"],
}


def read_data(prefixes_tsv_path, labels_tsv_path, dataset_path):
    prefixes = names.read_prefixes(prefixes_tsv_path)
    labels = names.read_labels(labels_tsv_path)

    dataset_yaml_path = os.path.join(dataset_path, "dataset.yml")
    with open(dataset_yaml_path, "r") as f:
        dataset = yaml.load(f, Loader=yaml.SafeLoader)

    fields = []
    for key, value in dataset.items():
        iri = None
        if names.is_id(prefixes, value):
            iri = names.id_to_iri(prefixes, value)
        label = value
        if value in labels:
            label = value + " " + labels[value]
        fields.append({"field": key, "iri": iri, "label": label, "value": value})

    assays_tsv_path = os.path.join(dataset_path, "assays.tsv")
    assays = []
    for row in tables.read_tsv(assays_tsv_path):
        assays.append(row)

    return {"dataset": dataset, "fields": fields, "assays": assays}


def write_xlsx(path, assay_type_id, rows=[]):
    """Write the assays submission template."""
    keys = None
    if assay_type_id in assay_types:
        keys = assay_types[assay_type_id]
    else:
        raise Exception("Unrecognize assay type: {0}".format(assay_type_id))

    assay_headers = [headers[key] for key in keys]

    instructions = """CoVIC-DB Dataset Submission

Add your results to the 'Dataset' sheet. Do not edit the other sheets.

Columns:
"""
    for header in assay_headers:
        instructions += "- {0}: {1}\n".format(header["label"], header["description"])

    instructions_rows = []
    for line in instructions.strip().splitlines():
        instructions_rows.append([grids.value_cell(line)])
    instructions_rows[0][0]["bold"] = True

    terminology_tables = OrderedDict()
    for header in assay_headers:
        if "terminology" in header:
            terminology_tables[header["label"]] = header["terminology"]
    terminology_tables_lengths = [len(t) for t in terminology_tables.values()]
    terminology_table = []

    for i in range(0, max(terminology_tables_lengths)):
        newrow = OrderedDict()
        for key, values in terminology_tables.items():
            newrow[key] = values[i] if i < len(values) else ""
        terminology_table.append(newrow)
    terminology_grid = grids.table_to_grid({}, {}, terminology_table)
    terminology_grid["title"] = "Terminology"
    terminology_grid["locked"] = True

    submission_grids = [
        {"title": "Instructions", "locked": True, "rows": instructions_rows},
        {
            "title": "Dataset",
            "active": True,
            "activeCell": "A2",
            "headers": [assay_headers],
            "rows": rows,
        },
        terminology_grid,
    ]

    workbooks.write_xlsx(submission_grids, path)


ids = {"Homo sapiens": "NCBITaxon:9606", "Mus musculus": "NCBITaxon:10090"}


def store_submission(assay_type_id, table):
    """Given the assay_type_id and a (validated!) antibody submission table,
    return a table of the submission."""
    keys = None
    if assay_type_id in assay_types:
        keys = assay_types[assay_type_id]
    else:
        raise Exception("Unrecognize assay type: {0}".format(assay_type_id))
    assay_headers = [headers[key] for key in keys]

    # TODO: actually store the data!
    return submissions.store(assay_headers, table)


def validate_submission(assay_type_id, table):
    """Given the assay_type_id and a submission table, return None if it is valid,
    otherwise return a grid with problems marked
    and an "errors" key with a list of errors."""
    keys = None
    if assay_type_id in assay_types:
        keys = assay_types[assay_type_id]
    else:
        raise Exception("Unrecognize assay type: {0}".format(assay_type_id))
    assay_headers = [headers[key] for key in keys]

    return submissions.validate(assay_headers, table)


### Validate Excel
#
# These validation methods read Excel (.xlsx) files
# and return a response dictionary that looks like an HTML reponse
# with some extra fields. See the `responses` module.


def validate_xlsx(assay_type_id, source):
    """Given a submitted_id string, a submitter_label string,
    and a file-like object (path, BytesIO) for an XLSX file,
    validate it the file and return a response dictionary."""
    try:
        table = workbooks.read_xlsx(source, sheet="Dataset")
    except Exception as e:
        return {"status": 400, "message": "Could not create XLSX file", "exception": e}

    grid = validate_submission(assay_type_id, table)
    if grid:
        errors = grid["errors"]
        del grid["errors"]
        content = BytesIO()
        write_xlsx(content, assay_type_id, grid["rows"])
        return {
            "status": 400,
            "message": "Submitted table contains errors.",
            "errors": errors,
            "grid": grid,
            "filename": assay_type_labels[assay_type_id] + "-submission.xlsx",
            "content": content,
        }

    table = store_submission(assay_type_id, table)
    return {"status": 200, "message": "Success", "table": table}


def validate_request(assay_type_id, request_files):
    """Given an assay_type_id and a and Django request.FILES object with one file,
    read it, validate it, and return a response dictionary."""
    result = requests.read_file(request_files)
    if result["status"] != 200:
        return result
    return validate_xlsx(assay_type_id, result["content"])


def examples():
    """Write and test some examples."""
    fields = names.read_fields("ontology/fields.tsv")
    prefixes = names.read_prefixes("ontology/prefixes.tsv")

    # neutralization template
    assay_type_id = "OBI:0001643"
    assay_name = assay_type_names[assay_type_id] + "-submission"
    path = "examples/" + assay_name + ".xlsx"
    write_xlsx(path, assay_type_id)

    # neutralization valid data
    valid_data = [
        ["COVIC 1", "positive", "0.52"],
        ["COVIC 2", "negative", "20.2"],
        ["COVIC 3", "negative", "23.7"],
        ["COVIC 4", "positive", "1.5"],
        ["COVIC 5", "unknown", "3.6"],
        ["COVIC 6", "negative", "64"],
        ["COVIC 7", "", ""],
        ["COVIC 8", "", ""],
        ["COVIC 9", "", ""],
        ["COVIC 10", "", ""],
    ]
    valid_data_table = []
    for row in valid_data:
        a, q, t = row
        valid_data_table.append(
                OrderedDict({"Antibody name": a, "Qualitative measure": q, "Titer": t})
        )
    valid_data_grid = grids.table_to_grid({}, {}, valid_data_table)

    path = "examples/" + assay_name + "-valid.xlsx"
    write_xlsx(path, assay_type_id, valid_data_grid["rows"])
    response = validate_xlsx(assay_type_id, path)
    print(assay_name, "VALID", response)
    assert response["status"] == 200
    path = "build/" + assay_name + "-valid-expanded.tsv"
    tables.write_tsv(response["table"], path)
    path = "build/" + assay_name + "-valid-expanded.html"
    html = responses.to_html(response, prefixes=prefixes, fields=fields)
    templates.write_html("templates/grid.html", {"html": html}, path)

    # neutralization invalid data
    invalid_data_table = deepcopy(valid_data_table)
    invalid_data_table[1]["Antibody name"] = ""
    invalid_data_table[2]["Antibody name"] = "COVIC 1"
    invalid_data_table[4]["Qualitative measure"] = "postive"
    invalid_data_table[4]["Titer"] = "none"
    invalid_data_table[5]["Qualitative measure"] = "intermediate"
    invalid_data_table[6]["Titer"] = ""
    invalid_data_grid = grids.table_to_grid({}, {}, invalid_data_table)

    path = "examples/" + assay_name + "-invalid.xlsx"
    write_xlsx(path, assay_type_id, invalid_data_grid["rows"])
    response = validate_xlsx(assay_type_id, path)
    print(assay_name, "INVALID", response)
    assert response["status"] == 400
    path = "examples/" + assay_name + "-invalid-highlighted.xlsx"
    write_xlsx(path, assay_type_id, response["grid"]["rows"])
    path = "build/" + assay_name + "-invalid-highlighted.html"
    html = responses.to_html(response, prefixes=prefixes, fields=fields)
    templates.write_html("templates/grid.html", {"html": html}, path)

    # VLP ELISA template
    assay_type_id = "OBI:0000661"
    assay_name = assay_type_names[assay_type_id] + "-submission"
    path = "examples/" + assay_name + ".xlsx"
    write_xlsx(path, assay_type_id)

    # VLP ELISA valid data
    path = "examples/" + assay_name + "-valid.xlsx"
    valid_data = [
        ["COVIC 2", "positive", ""],
        ["COVIC 3", "positive", ""],
        ["COVIC 4", "positive", "also binds VP40 only VLP"],
        ["COVIC 5", "negative", ""],
        ["COVIC 6", "positive", ""],
        ["COVIC 7", "negative", "did not bind positive control"],
        ["COVIC 8", "positive", ""],
        ["COVIC 9", "negative", ""],
    ]
    valid_data_table = []
    for row in valid_data:
        a, q, c = row
        valid_data_table.append(
            OrderedDict({"Antibody name": a, "Qualitative measure": q, "Comment": c})
        )
    valid_data_grid = grids.table_to_grid({}, {}, valid_data_table)
    write_xlsx(path, assay_type_id, valid_data_grid["rows"])
    response = validate_xlsx(assay_type_id, path)
    print(assay_name, "VALID", response)
    assert response["status"] == 200
    path = "build/" + assay_name + "-valid-expanded.tsv"
    tables.write_tsv(response["table"], path)
    path = "build/" + assay_name + "-valid-expanded.html"
    html = responses.to_html(response, prefixes=prefixes, fields=fields)
    templates.write_html("templates/grid.html", {"html": html}, path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert dataset text files to HTML")
    parser.add_argument("template", type=str, help="The template to use")
    parser.add_argument("prefixes", type=str, help="The prefixes table")
    parser.add_argument("labels", type=str, help="The labels table")
    parser.add_argument("dataset", type=str, help="The dataset directory")
    parser.add_argument("output", type=str, help="The output file")
    args = parser.parse_args()

    templates.write_html(
        args.template, read_data(args.prefixes, args.labels, args.dataset), args.output
    )
