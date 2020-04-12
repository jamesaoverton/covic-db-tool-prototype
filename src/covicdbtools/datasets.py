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


def get_assay_type_id(assay_type):
    """Given an assay type name or ID, return the assay type ID."""
    assay_type_id = assay_type
    if names.is_id(config.prefixes, assay_type):
        return assay_type_id
    assay_name = assay_type.replace("-", " ")
    if assay_name not in config.ids:
        raise Exception(f"Unrecognized assay type: {assay_type}")
    assay_type_id = config.ids[assay_name]
    if assay_type_id not in assay_types:
        raise Exception(f"Not an assay type: {assay_type_id} {assay_type}")
    return assay_type_id


def get_assay_headers(assay_type):
    """Given an assay type name or ID, return the assay headers."""
    assay_type_id = get_assay_type_id(assay_type)
    return [headers[key] for key in assay_types[assay_type_id]]


def read_data(dataset_path):
    dataset_yaml_path = os.path.join(dataset_path, "dataset.yml")
    with open(dataset_yaml_path, "r") as f:
        dataset = yaml.load(f, Loader=yaml.SafeLoader)

    fields = []
    for key, value in dataset.items():
        iri = None
        if names.is_id(config.prefixes, value):
            iri = names.id_to_iri(config.prefixes, value)
        label = value
        if value in config.labels:
            label = value + " " + config.labels[value]
        fields.append({"field": key, "iri": iri, "label": label, "value": value})

    assays_tsv_path = os.path.join(dataset_path, "assays.tsv")
    assays = []
    for row in tables.read_tsv(assays_tsv_path):
        assays.append(row)

    return {"dataset": dataset, "fields": fields, "assays": assays}


def fill(assay_type, rows=[]):
    """Fill the assay submission template, returning a list of grids."""
    assay_headers = get_assay_headers(assay_type)

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

    return [
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


def validate(assay_type, table):
    """Given the assay_type_id and a submission table,
    validate it and return a response with "grid" and maybe "errors"."""
    assay_headers = get_assay_headers(assay_type)
    return submissions.validate(assay_headers, table)


if __name__ == "__main__":
    config.update()
    parser = argparse.ArgumentParser(description="Convert dataset text files to HTML")
    parser.add_argument("template", type=str, help="The template to use")
    parser.add_argument("dataset", type=str, help="The dataset directory")
    parser.add_argument("output", type=str, help="The output file")
    args = parser.parse_args()

    templates.write_html(args.template, read_data(args.dataset), args.output)
