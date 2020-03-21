#!/usr/bin/env python3

import argparse
import os

import tables
import names
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
    grid = names.table_to_grid(prefixes, fields, antibodies)
    grid["message"]: "These are all the antibodies in the system."
    return grid


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


def validate_xlsx(path):
    table = workbooks.read_xlsx(path)
    errors = []
    rows = []

    for row in table:
        newrow = []
        cell = None

        if not "Antibody name" in row or row["Antibody name"].strip() == "":
            comment = "Missing required value 'Antibody name'"
            cell = error_cell("", comment)
            errors.append(comment)
        else:
            cell = value_cell(row["Antibody name"])
        newrow.append(cell)

        if not "Host" in row or row["Host"].strip() == "":
            comment = "Missing required value 'Host'"
            cell = error_cell("", comment)
            errors.append(comment)
        elif row["Host"] not in ["Homo sapiens", "Mus musculus"]:
            comment = "'{0}' is not regognized host".format(row["Host"])
            cell = error_cell(row["Host"], comment)
            errors.append(comment)
        else:
            cell = value_cell(row["Host"])
        newrow.append(cell)

        if not "Isoform" in row or row["Isoform"].strip() == "":
            comment = "Missing required value 'Isoform'"
            cell = error_cell("", comment)
            errors.append(comment)
        else:
            cell = value_cell(row["Isoform"])
        newrow.append(cell)

        rows.append(newrow)

    if len(errors) > 0:
        return {"errors": errors, "headers": [headers], "rows": rows}
    return None


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
