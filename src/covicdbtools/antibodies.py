#!/usr/bin/env python3

import argparse

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
    submissions,
)
from covicdbtools.responses import success, failure


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


def fill(rows=[]):
    """Fill the antibodies submission template, returning a list of grids."""
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

    return [
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


def validate(table):
    """Given a table, validate and return a response with a "grid"."""
    return submissions.validate(headers, table)
