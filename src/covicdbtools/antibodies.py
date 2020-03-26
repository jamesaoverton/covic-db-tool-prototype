#!/usr/bin/env python3

import argparse

from collections import OrderedDict
from copy import deepcopy

from covicdbtools import (
    names,
    tables,
    grids,
    workbooks,
    templates,
    responses,
    submissions,
)

### Hardcoded fields
# TODO: Make this configurable

hosts_table = tables.read_tsv("ontology/hosts.tsv")
hosts = [h["label"] for h in hosts_table[1:]]

isotypes_table = tables.read_tsv("ontology/isotypes.tsv")
heavy_chains = [i["label"] for i in isotypes_table[1:] if i["chain type"] == "heavy"]
light_chains = [i["label"] for i in isotypes_table[1:] if i["chain type"] == "light"]

headers = [
    {
        "value": "ab_label",
        "label": "Antibody name",
        "description": "Your institution's preferred name for the antibody.",
        "locked": True,
        "required": True,
        "unique": True,
    },
    {
        "value": "host_label",
        "label": "Host",
        "description": "The name of the host species that is the source of the antibody.",
        "locked": True,
        "required": True,
        "terminology": hosts,
        "validations": [
            {
                "type": "list",
                "formula1": "=Terminology!$A$2:$A${0}".format(len(hosts) + 1),
                "allow_blank": True,
            }
        ],
    },
    {
        "value": "isotype_label",
        "label": "Isotype",
        "description": "The name of the isotype of the antibody's heavy chain.",
        "locked": True,
        "required": True,
        "terminology": heavy_chains,
        "validations": [
            {
                "type": "list",
                "formula1": "=Terminology!$B$2:$B${0}".format(len(heavy_chains) + 1),
                "allow_blank": True,
            }
        ],
    },
]


def read_antibodies(id_to_label, antibodies_tsv_path):
    return names.label_tsv(id_to_label, antibodies_tsv_path)


def read_data(prefixes_tsv_path, fields_tsv_path, labels_tsv_path, antibodies_tsv_path):
    prefixes = names.read_prefixes(prefixes_tsv_path)
    labels = names.read_labels(labels_tsv_path)
    fields = names.read_fields(fields_tsv_path)
    antibodies = read_antibodies(labels, antibodies_tsv_path)
    grid = grids.table_to_grid(prefixes, fields, antibodies)
    grid["message"]: "These are all the antibodies in the system."
    return grid


def write_xlsx(path, rows=[]):
    """Write the antibodies submission template."""
    instructions = """CoVIC-DB Antibodies Submission

Add your antibodies to the 'Antibodies' sheet. Do not edit the other sheets.

Columns:
"""
    for header in headers:
        instructions += "- {0}: {1}\n".format(header["label"], header["description"])

    instructions_rows = []
    for line in instructions.strip().splitlines():
        instructions_rows.append([grids.value_cell(line)])
    instructions_rows[0][0]["bold"] = True

    terminology_tables = OrderedDict()
    for header in headers:
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
            "title": "Antibodies",
            "active": True,
            "activeCell": "A2",
            "headers": [headers],
            "rows": rows,
        },
        terminology_grid,
    ]

    workbooks.write_xlsx(submission_grids, path)


# TODO: Make this configurable
ids = {"Homo sapiens": "NCBITaxon:9606", "Mus musculus": "NCBITaxon:10090"}


def store_submission(submitter_id, submitter_label, table):
    """Given the IDs map, a submitter label, and a (validated!) antibody submission table,
    return a table of the submission."""

    # TODO: Reuse submissions.store()
    submission = []
    for row in table:
        newrow = OrderedDict()
        newrow["ab_label"] = row["Antibody name"]
        newrow["submitter_id"] = submitter_id
        newrow["submitter_label"] = submitter_label
        newrow["host_type_id"] = ids[row["Host"]]
        newrow["host_type_label"] = row["Host"]
        newrow["isotype"] = row["Isotype"]
        submission.append(newrow)

    # TODO: actually store the data!
    return submission


def validate_submission(table):
    """Given the IDs map and a submission table, return None if it is valid,
    otherwise return a grid with problems marked
    and an "errors" key with a list of errors."""
    return submissions.validate(headers, table)


### Validate Excel
#
# These validation methods read Excel (.xlsx) files
# and return a response dictionary that looks like an HTML reponse
# with some extra fields. See the `responses` module.


def validate_xlsx(submitter_id, submitter_label, path):
    """Given a submitted_id string, a submitter_label string, and an XLSX file path,
    validate it the file and return a response dictionary."""
    try:
        table = workbooks.read_xlsx(path, sheet="Antibodies")
    except Exception as e:
        return {"status": 400, "message": "Could not create XLSX file", "exception": e}

    grid = validate_submission(table)
    if grid:
        errors = grid["errors"]
        del grid["errors"]
        return {
            "status": 400,
            "message": "Submitted table contains errors.",
            "errors": errors,
            "grid": grid,
        }

    table = store_submission(submitter_id, submitter_label, table)
    return {"status": 200, "message": "Success", "table": table}


def validate_request(submitter_id, submitter_label, request_files):
    """Given a submitted_id string, a submitter_label string,
    and Django request.FILES object with one file,
    store it in a temporary file, validate it, and return a response dictionary."""
    result = requests.store_file(request_files)
    if result:
        return result

    return validate_xlsx(submitter_id, submitter_label, path)


def examples():
    """Write and test some examples."""
    fields = names.read_fields("ontology/fields.tsv")
    prefixes = names.read_prefixes("ontology/prefixes.tsv")

    valid_data = [
        ["VD-Crotty 1", "Homo sapiens", "IgA"],
        ["VD-Crotty 2", "Homo sapiens", "IgD"],
        ["VD-Crotty 3", "Mus musculus", "IgG"],
        ["VD-Crotty 4", "Homo sapiens", "IgG2a"],
        ["VD-Crotty 5", "Mus musculus", "IgA1"],
        ["VD-Crotty 6", "Mus musculus", "IgA"],
        ["VD-Crotty 7", "Homo sapiens", "IgE"],
        ["VD-Crotty 8", "Mus musculus", "IgA2"],
        ["VD-Crotty 9", "Homo sapiens", "IgG1"],
        ["VD-Crotty 10", "Mus musculus", "IgM"],
    ]
    valid_data_table = []
    for row in valid_data:
        a, h, i = row
        valid_data_table.append(
            OrderedDict({"Antibody name": a, "Host": h, "Isotype": i})
        )
    valid_data_grid = grids.table_to_grid({}, {}, valid_data_table)

    invalid_data = [
        ["A6", "Homo sapiens", "IgA"],
        ["B12", "Mus musculus", "IgD"],
        ["", "Mus musculus", "IgD"],
        ["C2", "Mus musculus", "IgG"],
        ["C3", "Homo sapiens", "IgG2a"],
        ["C6", "", "Ig1"],
        ["D12", "Homo sapiens", "IgE"],
        ["E8", "Mus musclus", "Igm"],
        ["C3", "Homo sapiens", "IgG2a"],
    ]
    invalid_data_table = []
    for row in invalid_data:
        a, h, i = row
        invalid_data_table.append(
            OrderedDict({"Antibody name": a, "Host": h, "Isotype": i})
        )
    invalid_data_grid = grids.table_to_grid({}, {}, invalid_data_table)

    path = "examples/antibodies-submission.xlsx"
    write_xlsx(path)

    path = "examples/antibodies-submission-valid.xlsx"
    write_xlsx(path, valid_data_grid["rows"])

    path = "examples/antibodies-submission-invalid.xlsx"
    write_xlsx(path, invalid_data_grid["rows"])

    submitter_id = "org:2"
    submitter_label = "Vanderbilt"
    response = validate_xlsx(submitter_id, submitter_label, path)
    print("INVALID", response)
    path = "examples/antibodies-submission-invalid-highlighted.xlsx"
    write_xlsx(path, response["grid"]["rows"])

    path = "build/antibodies-submission-invalid-highlighted.html"
    html = responses.to_html(response, prefixes=prefixes, fields=fields)
    templates.write_html("templates/grid.html", {"html": html}, path)

    submitter_id = "org:1"
    submitter_label = "LJI"
    path = "examples/antibodies-submission-valid.xlsx"
    response = validate_xlsx(submitter_id, submitter_label, path)
    print("VALID", response)
    path = "build/antibodies-submission-valid-expanded.tsv"
    tables.write_tsv(response["table"], path)
    path = "build/antibodies-submission-valid-expanded.html"
    html = responses.to_html(response, prefixes=prefixes, fields=fields)
    templates.write_html("templates/grid.html", {"html": html}, path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert antibodies table to HTML")
    parser.add_argument("template", type=str, help="The template to use")
    parser.add_argument("prefixes", type=str, help="The prefixes table")
    parser.add_argument("fields", type=str, help="The fields table")
    parser.add_argument("labels", type=str, help="The labels table")
    parser.add_argument("antibodies", type=str, help="The antibodies table")
    parser.add_argument("output", type=str, help="The output file")
    args = parser.parse_args()

    templates.write_html(
        args.template,
        read_data(args.prefixes, args.fields, args.labels, args.antibodies),
        args.output,
    )
