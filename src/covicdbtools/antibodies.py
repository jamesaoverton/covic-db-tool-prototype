#!/usr/bin/env python3

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
    responses,
    submissions,
)
from covicdbtools.responses import success, failure, failed


hosts = list(config.hosts.keys())

isotypes = [i["label"] for i in config.isotypes.values()]
light_chains = [i["label"] for i in config.light_chains.values()]
heavy_chain_germline = [i["label"] for i in config.heavy_chain_germline.values()]


headers = [
    {
        "value": "ab_name",
        "label": "Antibody name",
        "description": "Your preferred code name for the antibody",
        "locked": True,
        "required": True,
        "unique": True,
    },
    {
        "value": "host_label",
        "label": "Host",
        "description": "Specify the host species that is the source of the antibody",
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
        "description": "Specify the antibody isotype, if known",
        "locked": True,
        "terminology": isotypes,
        "validations": [
            {
                "type": "list",
                "formula1": "=Terminology!$B$2:$B${0}".format(len(isotypes) + 1),
                "allow_blank": True,
            }
        ],
    },
    {
        "value": "light_chain_label",
        "label": "Light chain",
        "description": "Specify the antibody light chain, if known (kappa or lambda)",
        "locked": True,
        "terminology": light_chains,
        "validations": [
            {
                "type": "list",
                "formula1": "=Terminology!$C$2:$C${0}".format(len(light_chains) + 1),
                "allow_blank": True,
            }
        ],
    },
    {
        "value": "heavy_chain_germline_label",
        "label": "Heavy chain germline",
        "description": "Specify the antibody heavy chain germline gene, if known",
        "locked": True,
        "terminology": heavy_chain_germline,
        "validations": [
            {
                "type": "list",
                "formula1": "=Terminology!$D$2:$D${0}".format(len(heavy_chain_germline) + 1),
                "allow_blank": True,
            }
        ],
    },
    {
        "value": "ab_details",
        "label": "Antibody details",
        "description": """Measurements or characteristics of the antibody.
This column is optional, and meant to capture data you might have on the antibody.
These data will not be released to the partner reference labs that will perform the analyses.
For example:
- Affinity: Spike protein binding affinity; inhibition of ACE2 binding; ELISA for Spike
- Neutralization: IC50 value
- Neutralization assay platform
- Epitope: Binning or competition data""",
        "locked": True,
    },
    {
        "value": "ab_structure",
        "label": "Structural data",
        "description": """Would you like structural analyses of this antibody?
If no, leave blank.
If yes, rank the antibodies in order of priority, starting with '1' for the highest priority.""",
        "type": "integer",
        "locked": True,
    },
    {
        "value": "ab_comment",
        "label": "Antibody comment",
        "description": "Please provide any other details about the antibody.",
        "locked": True,
    },
]


def fill(rows=[]):
    """Fill the antibodies submission template, returning a list of grids."""
    instructions_rows = []
    instructions = """CoVIC-DB Antibodies Submission
Version 1.2.2

Add your antibodies to the 'Antibodies' sheet.
Do not change the headers of the 'Antibodies' sheet.
Do not edit the other sheets.
"""
    for line in instructions.strip().splitlines():
        instructions_rows.append([grids.value_cell(line)])
    instructions_rows[0][0]["bold"] = True
    instructions_rows[0][0]["width"] = 18
    instructions_rows[0].append(grids.value_cell(""))
    instructions_rows[0][1]["width"] = 70
    instructions_rows.append([])

    for header in headers:
        description = header["description"].strip().splitlines()
        d = description.pop(0)
        instructions_rows.append([grids.value_cell(header["label"]), grids.value_cell(d)])
        instructions_rows[-1][0]["bold"] = True
        for d in description:
            instructions_rows.append([grids.value_cell(""), grids.value_cell(d)])
    instructions_rows[-1][0]["bold"] = True

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
    table = response["table"]  # blank rows removed

    if not config.secret:
        return failure("CVDB_SECRET directory is not configured")
    secret = []
    path = os.path.join(config.secret.working_tree_dir, "antibodies.tsv")
    if os.path.isfile(path):
        secret = tables.read_tsv(path)

    if not config.staging:
        return failure("CVDB_STAGING directory is not configured")
    blind = []
    path = os.path.join(config.staging.working_tree_dir, "antibodies.tsv")
    if os.path.isfile(path):
        blind = tables.read_tsv(path)

    if len(secret) != len(blind):
        return failure(f"Different number of antibody rows: {len(secret)} != {len(blind)}")

    current_id = "COVIC:0"
    if len(blind) > 0:
        current_id = blind[-1]["ab_id"]

    submission = []
    for row in table:
        current_id = names.increment_id(current_id)

        # secrets: write this to the secret repo
        secret_row = OrderedDict()
        secret_row["ab_id"] = current_id
        secret_row["ab_name"] = row["Antibody name"]
        secret_row["ab_details"] = row["Antibody details"]
        secret_row["ab_comment"] = row["Antibody comment"]
        secret_row["org_name"] = organization
        secret_row["submitter_email"] = email
        secret.append(secret_row)

        # blind: write this to staging/public repos
        blind_row = OrderedDict()
        blind_row["ab_id"] = current_id

        # submission: return this to the submitter
        submission_row = OrderedDict()
        submission_row["ab_id"] = current_id
        submission_row["ab_name"] = row["Antibody name"]

        # for each header, add cells to blind and submission
        for header in headers[1:]:
            column = header["value"]
            value = row[header["label"]]
            if column.endswith("_label"):
                i = config.ids.get(value, "")
                blind_row[column.replace("_label", "_id")] = i
                submission_row[column.replace("_label", "_id")] = i
                submission_row[column] = value
            else:
                blind_row[column] = value
                submission_row[column] = value

        blind.append(blind_row)
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
        config.secret.index.commit("Submit antibodies", author=author, committer=config.covic)
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
        config.staging.index.commit("Submit antibodies", author=author, committer=config.covic)
    except Exception as e:
        return failure(f"Failed to commit '{path}'", {"exception": e})

    # public
    if not config.public:
        return failure("CVDB_PUBLIC directory is not configured")
    try:
        path = os.path.join(config.public.working_tree_dir, "antibodies.tsv")
        tables.write_tsv(blind, path)
    except Exception as e:
        return failure(f"Failed to write '{path}'", {"exception": e})
    try:
        config.public.index.add([path])
        config.public.index.commit("Submit antibodies", author=config.covic, committer=config.covic)
    except Exception as e:
        return failure(f"Failed to commit '{path}'", {"exception": e})

    grid = grids.table_to_grid(config.prefixes, config.fields, submission)
    print("Submitted antibodies")
    return success({"table": submission, "grid": grid})
