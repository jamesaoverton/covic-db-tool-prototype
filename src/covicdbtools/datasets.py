#!/usr/bin/env python3

import argparse
import os
import yaml

from collections import OrderedDict
from io import BytesIO

from covicdbtools import (
    config,
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
        "type": "float",
    },
    "comment": {
        "value": "comment",
        "label": "Comment",
        "description": "A free-text comment on the assay",
        "locked": True,
    },
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
    return submissions.store({}, assay_headers, table)


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
            "filename": config.labels[assay_type_id].replace(" ", "-")
            + "-submission.xlsx",
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
