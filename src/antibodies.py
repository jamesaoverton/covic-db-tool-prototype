#!/usr/bin/env python3

import argparse
import datetime
import os

import tables
import names
import grids
import templates
import workbooks

from collections import OrderedDict


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


# TODO: Make this configurable
headers = [
    {"label": "Antibody name", "value": "ab_label"},
    {"label": "Host", "value": "host_label"},
    {"label": "Isoform", "value": "isoform"},
]


def write_xlsx(path):
    grid = {"headers": [headers]}
    sheets = [["Antibodies", grid]]
    workbooks.write_xlsx(sheets, path)


def value_cell(value):
    return {"label": value, "value": value}


def error_cell(value, comment):
    return {"label": value, "value": value, "status": "ERROR", "comment": comment}


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
        newrow["isoform"] = row["Isoform"]
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
            cell = error_cell("", comment)
            errors.append("Error in row {0}: {1}".format(i + 1, comment))
        else:
            cell = value_cell(row["Antibody name"])
        newrow.append(cell)

        if not "Host" in row or row["Host"].strip() == "":
            comment = "Missing required value 'Host'"
            cell = error_cell("", comment)
            errors.append("Error in row {0}: {1}".format(i + 1, comment))
        # TODO: Make this configurable.
        elif row["Host"] not in ["Homo sapiens", "Mus musculus"]:
            comment = "'{0}' is not a recognized host".format(row["Host"])
            cell = error_cell(row["Host"], comment)
            errors.append("Error in row {0}: {1}".format(i + 1, comment))
        else:
            cell = value_cell(row["Host"])
        newrow.append(cell)

        if not "Isoform" in row or row["Isoform"].strip() == "":
            comment = "Missing required value 'Isoform'"
            cell = error_cell("", comment)
            errors.append("Error in row {0}: {1}".format(i + 1, comment))
        else:
            cell = value_cell(row["Isoform"])
        newrow.append(cell)

        rows.append(newrow)

    if len(errors) > 0:
        return {"errors": errors, "headers": [headers], "rows": rows}
    return None


def validate_xlsx(submitter_id, submitter_label, path):
    try:
        table = workbooks.read_xlsx(path)
    except Exception as e:
        return {"status": 400, "message": "Could not create XLSX file", "exception": e}

    result = validate_submission(table)
    if result and "errors" in result and len(result["errors"]) > 0:
        result.update({"status": 400, "message": "Submitted table contains errors."})
        return result

    result = store_submission(submitter_id, submitter_label, table)
    return result


def validate_request(submitter_id, submitter_label, request_files):
    """Given a Django request.FILES object, store it in a temporary file,
    validate it, and return a message."""
    if len(request_files.keys()) > 0:
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
