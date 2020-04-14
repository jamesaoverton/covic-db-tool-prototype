#!/usr/bin/env python3

import argparse
import os
import re
import shutil
import yaml

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
    assay_type_id = None
    if names.is_id(config.prefixes, assay_type):
        assay_type_id = assay_type
    else:
        assay_name = assay_type.replace("-", " ")
        if assay_name in config.ids:
            assay_type_id = config.ids[assay_name]
        else:
            if not config.staging:
                raise Exception("CVDB_STAGING directory is not configured")
            path = os.path.join(
                config.staging.working_tree_dir, "datasets", assay_type, "dataset.yml"
            )
            if os.path.isfile(path):
                with open(path, "r") as f:
                    dataset = yaml.load(f, Loader=yaml.SafeLoader)
                if "Assay type ID" in dataset:
                    assay_type_id = dataset["Assay type ID"]
    if not assay_type_id:
        raise Exception(f"Unrecognized assay type: {assay_type}")
    if assay_type_id not in assay_types:
        raise Exception(f"Not an assay type: {assay_type_id} {assay_type}")
    return assay_type_id


def get_assay_headers(assay_type):
    """Given an assay type name or ID, return the assay headers."""
    assay_type_id = get_assay_type_id(assay_type)
    return [headers[key] for key in assay_types[assay_type_id]]


def get_status(dataset_id):
    if not config.staging:
        raise Exception("CVDB_STAGING directory is not configured")
    path = os.path.join(
        config.staging.working_tree_dir, "datasets", str(dataset_id), "dataset.yml"
    )
    if os.path.isfile(path):
        with open(path, "r") as f:
            dataset = yaml.load(f, Loader=yaml.SafeLoader)
            return dataset.get("Dataset status", "submitted")
    return None


def set_status(dataset_id, status):
    if not config.staging:
        raise Exception("CVDB_STAGING directory is not configured")
    path = os.path.join(
        config.staging.working_tree_dir, "datasets", str(dataset_id), "dataset.yml"
    )
    with open(path, "r") as f:
        dataset = yaml.load(f, Loader=yaml.SafeLoader)
        dataset["Dataset status"] = status
        with open(path, "w") as outfile:
            yaml.dump(dataset, outfile, sort_keys=False)


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
    validate it and return a response with "grid" and maybe "errors",
    and an Excel file as "content"."""
    assay_headers = get_assay_headers(assay_type)
    response = submissions.validate(assay_headers, table)
    grids = fill(assay_type, response["grid"]["rows"])
    content = BytesIO()
    workbooks.write(grids, content)
    response["content type"] = responses.xlsx
    response["content"] = content
    return response


def create(name, email, assay_type):
    if not config.staging:
        return Failure("CVDB_STAGING directory is not configured")

    assay_type_id = get_assay_type_id(assay_type)
    datasets_path = os.path.join(config.staging.working_tree_dir, "datasets")
    current_id = 0
    if not os.path.exists(datasets_path):
        os.makedirs(datasets_path)
    if not os.path.isdir(datasets_path):
        return failure(f"'{datasets_path}' is not a directory")
    for root, dirs, files in os.walk(datasets_path):
        for name in dirs:
            if re.match(r"\d+", name):
                current_id = max(current_id, int(name))
    dataset_id = current_id + 1

    author = Actor(name, email)

    # staging
    try:
        dataset_path = os.path.join(datasets_path, str(dataset_id))
        os.mkdir(dataset_path)
    except Exception as e:
        return failure(f"Failed to create '{dataset_path}'", {"exception": e})
    try:
        dataset = {
            "Dataset ID": f"ds:{dataset_id}",
            "Dataset status": "submitted",
            "Assay type ID": assay_type_id,
        }
        path = os.path.join(dataset_path, "dataset.yml")
        with open(path, "w") as outfile:
            yaml.dump(dataset, outfile, sort_keys=False)
    except Exception as e:
        return failure(f"Failed to write '{path}'", {"exception": e})
    try:
        config.staging.index.add([path])
        config.staging.index.commit(
            f"Create dataset {dataset_id}", author=author, committer=config.covic
        )
    except Exception as e:
        return failure(f"Failed to commit '{path}'", {"exception": e})

    print(f"Created dataset {dataset_id}")
    return success({"dataset_id": dataset_id})


def submit(name, email, dataset_id, table):
    """Given a dataset ID and a new table of assays,
    validate it, save it to staging, and commit."""
    response = validate(dataset_id, table)
    if failed(response):
        return response

    author = Actor(name, email)

    # staging
    if not config.staging:
        return Failure("CVDB_STAGING directory is not configured")
    dataset_path = os.path.join(
        config.staging.working_tree_dir, "datasets", str(dataset_id)
    )
    paths = []
    try:
        set_status(dataset_id, "submitted")
        path = os.path.join(dataset_path, "dataset.yml")
        paths.append(path)
    except Exception as e:
        return failure(f"Failed to update dataset status", {"exception": e})
    try:
        path = os.path.join(dataset_path, "assays.tsv")
        tables.write_tsv(table, path)
        paths.append(path)
    except Exception as e:
        return failure(f"Failed to write '{path}'", {"exception": e})
    try:
        config.staging.index.add(paths)
        config.staging.index.commit(
            f"Submit assays to dataset {dataset_id}",
            author=author,
            committer=config.covic,
        )
    except Exception as e:
        return failure(f"Failed to commit '{path}'", {"exception": e})

    print(f"Submitted assays to dataset {dataset_id}")
    return success({"dataset_id": dataset_id})


def promote(name, email, dataset_id):
    author = Actor(name, email)

    # staging
    if not config.staging:
        return Failure("CVDB_STAGING directory is not configured")
    staging_dataset_path = os.path.join(
        config.staging.working_tree_dir, "datasets", str(dataset_id)
    )
    paths = []
    try:
        set_status(dataset_id, "promoted")
        path = os.path.join(staging_dataset_path, "dataset.yml")
        paths.append(path)
    except Exception as e:
        return failure(f"Failed to update dataset status", {"exception": e})
    try:
        config.staging.index.add(paths)
        config.staging.index.commit(
            f"Promote dataset {dataset_id}", author=author, committer=config.covic
        )
    except Exception as e:
        return failure(f"Failed to commit '{path}'", {"exception": e})

    # public
    if not config.public:
        return Failure("CVDB_PUBLIC directory is not configured")
    public_dataset_path = os.path.join(
        config.public.working_tree_dir, "datasets", str(dataset_id)
    )
    try:
        os.makedirs(public_dataset_path)
    except Exception as e:
        return failure(f"Could not create '{path}'", {"exception": e})
    try:
        paths = []
        for filename in ["dataset.yml", "assays.tsv"]:
            src = os.path.join(staging_dataset_path, filename)
            dst = os.path.join(public_dataset_path, filename)
            shutil.copyfile(src, dst)
            paths.append(dst)
    except Exception as e:
        return failure(f"Could not copy '{src}' to '{dst}'", {"exception": e})
    try:
        config.public.index.add(paths)
        config.public.index.commit(
            f"Promote dataset {dataset_id}", author=config.covic, committer=config.covic
        )
    except Exception as e:
        return failure(f"Failed to commit '{public_dataset_path}'", {"exception": e})

    print(f"Promoted dataset {dataset_id} from staging to public")
    return success({"dataset_id": dataset_id})


if __name__ == "__main__":
    config.update()
    parser = argparse.ArgumentParser(description="Convert dataset text files to HTML")
    parser.add_argument("template", type=str, help="The template to use")
    parser.add_argument("dataset", type=str, help="The dataset directory")
    parser.add_argument("output", type=str, help="The output file")
    args = parser.parse_args()

    templates.write_html(args.template, read_data(args.dataset), args.output)
