#!/usr/bin/env python3

import argparse
import os

from collections import OrderedDict
from copy import deepcopy
from datetime import datetime

from covicdbtools import names, tables, grids, workbooks, templates

### Hardcoded fields
# TODO: Make this configurable

instructions = """CoVIC-DB Antibodies Submission

Add your antibodies to the 'Antibodies' sheet. Do not edit the other sheets.

Columns:
- Antibody name: Your institutions preferred name for the antibody.
- Host: The name of the host species that is the source of the antibody.
- Isotype: The name of the isotype of the antibody's heavy chain.
"""

hosts = ["Homo sapiens", "Mus musculus"]

isotypes = [
    "IgA",
    "IgA1",
    "IgA2",
    "IgD",
    "IgE",
    "IgG",
    "IgG1",
    "IgG2",
    "IgG2a",
    "IgG2b",
    "IgG2c",
    "IgG3",
    "IgG4",
    "IgM",
    "sIgA",
]


headers = [
    {"label": "Antibody name", "value": "ab_label", "locked": True},
    {
        "label": "Host",
        "value": "host_label",
        "locked": True,
        "validations": [
            {
                "type": "list",
                "formula1": "=Terminology!A2:A{0}".format(len(hosts) + 1),
                "allow_blank": True,
            }
        ],
    },
    {
        "label": "Isotype",
        "value": "isotype",
        "locked": True,
        "validations": [
            {
                "type": "list",
                "formula1": "=Terminology!B2:B{0}".format(len(isotypes) + 1),
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
    instructions_rows = []
    for line in instructions.strip().splitlines():
        instructions_rows.append([grids.value_cell(line)])
    instructions_rows[0][0]["bold"] = True

    terminology_table = []
    for i in range(0, max(len(hosts), len(isotypes))):
        host = hosts[i] if i < len(hosts) else ""
        isotype = isotypes[i] if i < len(isotypes) else ""
        terminology_table.append(OrderedDict({"Host": host, "Isotype": isotype}))
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
    assign IDs return a table of submission."""
    antibodies = tables.read_tsv("data/antibodies.tsv")
    current_id = antibodies[-1]["ab_id"]

    submission = []
    for row in table:
        newrow = OrderedDict()
        current_id = names.increment_id(current_id)
        newrow["ab_id"] = current_id
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
    errors = []
    rows = []

    for i in range(0, len(table)):
        row = table[i]
        newrow = []
        cell = None

        if not "Antibody name" in row or row["Antibody name"].strip() == "":
            comment = "Missing required value 'Antibody name'"
            cell = grids.error_cell("", comment)
            errors.append("Error in row {0}: {1}".format(i + 1, comment))
        else:
            cell = grids.value_cell(row["Antibody name"])
        newrow.append(cell)

        if not "Host" in row or row["Host"].strip() == "":
            comment = "Missing required value 'Host'"
            cell = grids.error_cell("", comment)
            errors.append("Error in row {0}: {1}".format(i + 1, comment))
        # TODO: Make this configurable.
        elif row["Host"] not in hosts:
            comment = "'{0}' is not a recognized host".format(row["Host"])
            cell = grids.error_cell(row["Host"], comment)
            errors.append("Error in row {0}: {1}".format(i + 1, comment))
        else:
            cell = grids.value_cell(row["Host"])
        newrow.append(cell)

        if not "Isotype" in row or row["Isotype"].strip() == "":
            comment = "Missing required value 'Isotype'"
            cell = grids.error_cell("", comment)
            errors.append("Error in row {0}: {1}".format(i + 1, comment))
        elif row["Isotype"] not in isotypes:
            comment = "'{0}' is not a recognized isotype".format(row["Isotype"])
            cell = grids.error_cell(row["Isotype"], comment)
            errors.append("Error in row {0}: {1}".format(i + 1, comment))
        else:
            cell = grids.value_cell(row["Isotype"])
        newrow.append(cell)

        rows.append(newrow)

    if len(errors) > 0:
        return {"errors": errors, "headers": [headers], "rows": rows}
    return None


### Validate Excel
#
# These validation methods read Excel (.xlsx) files
# and return a response dictionary that looks like an HTML reponse
# with some extra fields:
#
# {"status": 400,
#  "message": "There some sort of error",
#  "errors": ["List of errors"],
#  "exception": FooException,
#  "grid": {"headers": [[...]], "rows": [[...]]},
#  "table": [OrderedDict(...)],
#  "path": "/absolute/path/to/result.xlsx"
# }
#
# The response_to_html() function will render the response into nice HTML.


def response_to_html(response, prefixes={}, fields={}):
    lines = ["<div>"]
    if "message" in response:
        lines.append("  <p>{0}</p>".format(response["message"]))
    if "exception" in response:
        lines.append("  <p>{0}</p>".format(str(response["exception"])))
    if "errors" in response:
        lines.append("  <p>Errors</p>")
        lines.append("  <ul>")
        for error in response["errors"]:
            lines.append("    <li>{0}</li>".format(error))
        lines.append("  </ul>")
    if "grid" in response:
        lines.append(grids.grid_to_html(response["grid"]))
    elif "table" in response:
        lines.append(
            grids.grid_to_html(grids.table_to_grid(fields, fields, response["table"]))
        )
    lines.append("</div>")
    return "\n".join(lines)


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
    if len(request_files.keys()) > 1:
        return {"status": 400, "message": "Multiple upload files not allowed"}

    datestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")  # 20200322-084530-123456
    temp = os.path.join("temp", datestamp)
    try:
        os.makedirs(temp)
    except Exception as e:
        return {
            "status": 400,
            "message": "Could not create temp directory",
            "exception": e,
        }

    path = None
    try:
        for filename, upload_file in request_files:
            path = os.path.join(temp, filename)
            with open(path, "wb+") as f:
                for chunk in upload_file.chunks():
                    f.write(chunk)
            paths.append(path)
    except Exception as e:
        return {"status": 400, "message": "Invalid upload", "exception": e}

    return validate_xlsx(submitter_id, submitter_label, path)


def examples():
    """Write and test some examples."""
    submitter_id = "org:1"
    submitter_label = "Acme Corp."
    fields = names.read_fields("ontology/fields.tsv")
    prefixes = names.read_prefixes("ontology/prefixes.tsv")

    valid_data = [
        ["Acme mAb 1", "Homo sapiens", "IgA"],
        ["Acme mAb 2", "Homo sapiens", "IgD"],
        ["Acme mAb 3", "Mus musculus", "IgG"],
        ["Acme mAb 4", "Homo sapiens", "IgG2a"],
        ["Acme mAb 5", "Mus musculus", "IgA1"],
        ["Acme mAb 6", "Mus musculus", "IgA"],
        ["Acme mAb 7", "Homo sapiens", "IgE"],
        ["Acme mAb 8", "Mus musculus", "IgA2"],
        ["Acme mAb 9", "Homo sapiens", "IgG1"],
        ["Acme mAb 10", "Mus musculus", "IgM"],
    ]
    valid_data_table = []
    for row in valid_data:
        a, h, i = row
        valid_data_table.append(
            OrderedDict({"Antibody name": a, "Host": h, "Isotype": i})
        )
    valid_data_grid = grids.table_to_grid({}, {}, valid_data_table)

    invalid_data_table = deepcopy(valid_data_table)
    invalid_data_table[1]["Antibody name"] = ""
    invalid_data_table[3]["Host"] = ""
    invalid_data_table[4]["Host"] = "Mu musculus"
    invalid_data_table[5]["Host"] = "Coronavirus"
    invalid_data_table[7]["Isotype"] = ""
    invalid_data_table[8]["Isotype"] = "Ig"
    invalid_data_grid = grids.table_to_grid({}, {}, invalid_data_table)

    path = "examples/antibodies-submission-valid.xlsx"
    write_xlsx(path)

    path = "examples/antibodies-submission-valid.xlsx"
    write_xlsx(path, valid_data_grid["rows"])

    path = "examples/antibodies-submission-invalid.xlsx"
    write_xlsx(path, invalid_data_grid["rows"])

    response = validate_xlsx(submitter_id, submitter_label, path)
    print("INVALID", response)
    path = "examples/antibodies-submission-invalid-highlighted.xlsx"
    write_xlsx(path, response["grid"]["rows"])

    path = "build/antibodies-submission-invalid-highlighted.html"
    html = response_to_html(response, prefixes=prefixes, fields=fields)
    templates.write_html("templates/grid.html", {"html": html}, path)

    path = "examples/antibodies-submission-valid.xlsx"
    response = validate_xlsx(submitter_id, submitter_label, path)
    print("VALID", response)
    path = "build/antibodies-submission-valid-expanded.tsv"
    tables.write_tsv(response["table"], path)
    path = "build/antibodies-submission-valid-expanded.html"
    html = response_to_html(response, prefixes=prefixes, fields=fields)
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
