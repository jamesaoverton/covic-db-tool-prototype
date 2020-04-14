#!/usr/bin/env python3

import argparse
import os

from collections import OrderedDict
from git import Actor
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
from covicdbtools.responses import success, failure, failed


### Hardcoded fields
# TODO: Make this configurable


hosts_table = tables.read_tsv("ontology/hosts.tsv")
hosts = [h["label"] for h in hosts_table[1:]]

isotypes_table = tables.read_tsv("ontology/isotypes.tsv")
heavy_chains = [i["label"] for i in isotypes_table[1:] if i["chain type"] == "heavy"]
light_chains = [i["label"] for i in isotypes_table[1:] if i["chain type"] == "light"]

headers = [
    {
        "value": "ab_name",
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
    {
        "value": "ab_details",
        "label": "Antibody details",
        "description": "Measurements or characteristics of the antibody",
        "locked": True,
    },
    {
        "value": "ab_comment",
        "label": "Antibody comment",
        "description": "Other comments on the antibody",
        "locked": True,
    },
]


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
    """Given a table,
    validate it and return a response with "grid" and maybe "errors",
    and an Excel file as "content"."""
    response = submissions.validate(headers, table)
    grids = fill(response["grid"]["rows"])
    content = BytesIO()
    workbooks.write(grids, content)
    response["content type"] = responses.xlsx
    response["content"] = content
    return response


def submit(name, email, organization, table):
    """Given a new table of antibodies:
    1. validate it
    2. assign IDs and append them to the secrets,
    3. append the blinded antibodies to the staging table,
    4. return a response with merged IDs."""
    response = validate(table)
    if failed(response):
        return response

    if not config.secret:
        return Failure("CVDB_SECRET directory is not configured")
    secret = []
    path = os.path.join(config.secret.working_tree_dir, "antibodies.tsv")
    if os.path.isfile(path):
        secret = tables.read_tsv(path)

    if not config.staging:
        return Failure("CVDB_STAGING directory is not configured")
    blind = []
    path = os.path.join(config.staging.working_tree_dir, "antibodies.tsv")
    if os.path.isfile(path):
        blind = tables.read_tsv(path)

    if len(secret) != len(blind):
        return failure(
            f"Different number of antibody rows: {len(secret)} != {len(blind)}"
        )

    current_id = "COVIC:0"
    if len(blind) > 0:
        current_id = blind[-1]["ab_id"]

    submission = []
    for row in table:
        current_id = names.increment_id(current_id)

        # secrets
        secret_row = OrderedDict()
        secret_row["ab_id"] = current_id
        secret_row["ab_name"] = row["Antibody name"]
        secret_row["ab_details"] = row["Antibody details"]
        secret_row["ab_comment"] = row["Antibody comment"]
        secret_row["organization"] = organization
        secret_row["submitter_name"] = name
        secret_row["submitter_email"] = email
        secret.append(secret_row)

        # blind
        blind_row = OrderedDict()
        blind_row["ab_id"] = current_id
        blind_row["host_type_id"] = config.ids[row["Host"]]
        blind_row["isotype_id"] = config.ids[row["Isotype"]]
        blind.append(blind_row)

        # submission
        submission_row = OrderedDict()
        submission_row["ab_id"] = current_id
        submission_row["ab_name"] = row["Antibody name"]
        submission_row["host_type_id"] = config.ids[row["Host"]]
        submission_row["host_type_label"] = row["Host"]
        submission_row["isotype_id"] = config.ids[row["Isotype"]]
        submission_row["isotype_label"] = row["Isotype"]
        submission_row["ab_details"] = row["Antibody details"]
        submission_row["ab_comment"] = row["Antibody comment"]
        submission.append(submission_row)

    author = Actor(name, email)

    # secret
    try:
        path = os.path.join(config.secret.working_tree_dir, "antibodies.tsv")
        tables.write_tsv(secret, path)
    except Exception as e:
        return failure(f"Failed to write '{path}'", {"exception": e})
    try:
        config.secret.index.add([path])
        config.secret.index.commit(
            f"Submit antibodies", author=author, committer=config.covic
        )
    except Exception as e:
        return failure(f"Failed to commit '{path}'", {"exception": e})

    # staging
    try:
        path = os.path.join(config.staging.working_tree_dir, "antibodies.tsv")
        tables.write_tsv(blind, path)
    except Exception as e:
        return failure(f"Failed to write '{path}'", {"exception": e})
    try:
        config.staging.index.add([path])
        config.staging.index.commit(
            f"Submit antibodies", author=author, committer=config.covic
        )
    except Exception as e:
        return failure(f"Failed to commit '{path}'", {"exception": e})

    # public
    if not config.public:
        return Failure("CVDB_PUBLIC directory is not configured")
    try:
        path = os.path.join(config.public.working_tree_dir, "antibodies.tsv")
        tables.write_tsv(blind, path)
    except Exception as e:
        return failure(f"Failed to write '{path}'", {"exception": e})
    try:
        config.public.index.add([path])
        config.public.index.commit(
            f"Submit antibodies", author=config.covic, committer=config.covic
        )
    except Exception as e:
        return failure(f"Failed to commit '{path}'", {"exception": e})

    grid = grids.table_to_grid(config.prefixes, config.fields, submission)
    print("Submitted antibodies")
    return success({"table": submission, "grid": grid})
