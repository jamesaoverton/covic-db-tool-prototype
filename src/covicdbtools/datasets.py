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
    tables,
    grids,
    workbooks,
    templates,
    responses,
    submissions,
)
from covicdbtools.responses import success, failure, failed


def get_staging_path(dataset_id):
    """Given a dataset ID, return the path to its staging directory."""
    return os.path.join(config.staging.working_tree_dir, "datasets", dataset_id)


def get_assay_header(column):
    """Given a column name that is an OBI or ONTIE ID
    (with an optional suffix for stddev, normalized, or qualitative),
    return the pair of a header dict and an error dict."""
    header = None
    assay_id = column.replace("obi_", "OBI:").replace("ontie_", "ONTIE:")
    if assay_id in config.labels and config.labels[assay_id] in config.assays:
        header = config.assays[config.labels[assay_id]].copy()
    elif assay_id in config.labels and config.labels[assay_id] in config.parameters:
        header = config.parameters[config.labels[assay_id]].copy()
    if header:
        return header, None

    root_id = (
        assay_id.replace("_stddev", "")
        .replace("_normalized", "")
        .replace("_qualitative", "")
        .replace("_fold_change", "")
    )
    if root_id not in config.labels:
        return None, failure(f"Unrecognized assay '{root_id}' for column '{column}'")
    root_label = config.labels[root_id]

    if root_label in config.assays:
        header = config.assays[root_label].copy()
    elif root_label in config.parameters:
        header = config.parameters[root_label].copy()
    else:
        return None, failure(f"Unrecognized assay '{root_id}' for column '{column}'")

    if column.endswith("_stddev"):
        header["label"] = f"Standard deviation in {header['units']}"
        header["description"] = f"The standard deviation of the value in '{root_label}'"
        header.pop("example", None)
    elif column.endswith("_normalized"):
        header["label"] = f"{root_label} normalized value"
        header["type"] = "score 0-1"
        header["description"] = f"The normalized value for '{root_label}' from 0-1"
        header.pop("example", None)
    elif column.endswith("_qualitative"):
        header["label"] = f"{root_label} qualitative value"
        header["type"] = "text"
        header["terminology"] = "qualitative_measures"
        header["description"] = f"The qualitative value for '{root_label}'"
        header.pop("example", None)
    elif column.endswith("_fold_change"):
        header["label"] = f"Fold-change {root_label}"
        header["description"] = f"The fold-change of '{root_label}' over virus control"
        header.pop("example", None)
    else:
        return None, failure(f"Unrecognized assay suffix for column '{column}'")

    return header, None


def get_assay_headers(dataset_id):
    """Given dataset ID, return the assay headers."""
    dataset_path = get_staging_path(dataset_id)
    if dataset_id == "spr":
        path = "examples/spr-dataset.yml"
    elif not config.staging:
        raise Exception("CVDB_STAGING directory is not configured")
    else:
        path = os.path.join(dataset_path, "dataset.yml")

    if not os.path.isfile(path):
        raise Exception(f"File does not exist '{path}'")
    with open(path, "r") as f:
        dataset = yaml.load(f, Loader=yaml.SafeLoader)
    columns = dataset["Columns"]

    headers = []
    terminology_count = 0
    for column in columns:
        header = None
        if column in config.fields:
            header = config.fields[column].copy()
        elif column.startswith("obi_") or column.startswith("ontie_"):
            header, error = get_assay_header(column)
            if error:
                return error
        if not header:
            return failure(f"Unrecognized column '{column}'")
        if not isinstance(header, dict):
            return failure(f"Error processing column '{column}': {header}")
        header["value"] = column
        header["locked"] = True
        if "terminology" in header and header["terminology"] != "":
            terms = list(getattr(config, header["terminology"]))
            col = chr(65 + terminology_count)
            end = len(terms) + 1
            formula = f"=Terminology!${col}$2:${col}${end}"
            header["terminology"] = terms
            header["validations"] = [{"type": "list", "formula1": formula, "allow_blank": True}]
            terminology_count += 1
        headers.append(header)

    return headers


def read_dataset_yml(dataset_id):
    """Given a dataset_id, return the dataset staging metadata."""
    path = os.path.join(get_staging_path(dataset_id), "dataset.yml")
    if os.path.isfile(path):
        with open(path, "r") as f:
            dataset = yaml.load(f, Loader=yaml.SafeLoader)
            dataset["Columns"] = get_assay_headers(dataset_id)
            return dataset
    raise Exception(f"No dataset found for '{dataset_id}'")


def get_value(scope, dataset_id, key=None):
    """Given a scope (staging or secret), a dataset ID, and an optional key,
    return the value or values from the dataset metadata."""
    if scope.casefold() == "secret":
        return get_secret_value(dataset_id, key)
    elif scope.casefold() == "staging":
        return get_staging_value(dataset_id, key)
    elif scope.casefold() == "all":
        return get_all_value(dataset_id, key)
    else:
        raise ValueError(f"Invalid scope '{scope}' for get_value")


def get_all_value(dataset_id, key=None):
    """Given a dataset ID and an optional key
    return the value or values from the all dataset metadata."""
    secrets = get_secret_value(dataset_id, key)
    if key and key in secrets:
        return secrets[key]
    staging = get_staging_value(dataset_id, key)
    if key and key in staging:
        return staging[key]
    if not key:
        staging["secrets"] = secrets
        return staging
    return None


def get_secret_value(dataset_id, key=None):
    """Given a dataset ID and an optional key
    return the value or values from the dataset secret metadata."""
    if key in ["ds_id"]:
        return failure(f"Key '{key}' cannot be updated")
    path = os.path.join(config.secret.working_tree_dir, "datasets.tsv")
    rows = tables.read_tsv(path)
    for row in rows:
        if row["ds_id"] == dataset_id:
            if key:
                return row[key]
            else:
                return row
    raise Exception(f"No row found for dataset '{dataset_id}'")


def get_staging_value(dataset_id, key=None):
    """Given a dataset ID and an optional key
    return the value or values from the dataset staging metadata."""
    if not config.staging:
        raise Exception("CVDB_STAGING directory is not configured")
    dataset = read_dataset_yml(dataset_id)
    if key:
        return dataset[key]
    else:
        return dataset


def set_value(scope, dataset_id, key, value):
    """Given a scope (staging or secret), a dataset ID, a key string, and a simle value,
    update the dataset metadata,
    maybe overwriting it."""
    if scope.casefold() == "secret":
        return set_secret_value(dataset_id, key, value)
    elif scope.casefold() == "staging":
        return set_staging_value(dataset_id, key, value)
    else:
        raise ValueError(f"Invalid scope '{scope}' for set_value")


def set_secret_value(dataset_id, key, value):
    """Given a dataset ID, key, and value,
    update the secret `datasets.tsv`."""
    if key in ["ds_id"]:
        return failure(f"Key '{key}' cannot be updated")
    path = os.path.join(config.secret.working_tree_dir, "datasets.tsv")
    rows = tables.read_tsv(path)
    done = False
    for row in rows:
        if row["ds_id"] == dataset_id:
            row[key] = str(value)
            done = True
        elif key not in row:
            row[key] = None
    if done:
        tables.write_tsv(rows, path)
    else:
        raise Exception(f"No row found for dataset '{dataset_id}'")


def set_staging_value(dataset_id, key, value):
    """Given a dataset ID, a key string, and a value string,
    that can be represented in YAML,
    update the staging `dataset.yml` file."""
    if not config.staging:
        raise Exception("CVDB_STAGING directory is not configured")
    path = os.path.join(config.staging.working_tree_dir, "datasets", str(dataset_id), "dataset.yml")
    parsed = yaml.load(value, Loader=yaml.SafeLoader)
    with open(path, "r") as f:
        dataset = yaml.load(f, Loader=yaml.SafeLoader)
        dataset[key] = parsed
        with open(path, "w") as outfile:
            yaml.dump(dataset, outfile, sort_keys=False)


def read_data(dataset_id):
    """Read the metadata and data for a dataset."""
    dataset = read_dataset_yml(dataset_id)

    assays_tsv_path = os.path.join(get_staging_path(dataset_id), "assays.tsv")
    assays = []
    for row in tables.read_tsv(assays_tsv_path):
        assays.append(row)

    return {"dataset": dataset, "assays": assays}


def fill(assay_type, rows=[]):
    """Fill the assay submission template, returning a list of grids."""
    assay_headers = get_assay_headers(assay_type)

    instructions = """CoVIC-DB Dataset Submission

Add your results to the 'Dataset' sheet. Do not edit the other sheets.

Columns:
"""
    for header in assay_headers:
        example = ""
        if "example" in header and header["example"].strip():
            example = f" (e.g. {header['example']})"
        instructions += f"- {header['label']}: {header['description']}{example}\n"

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

    if len(terminology_tables) > 0:
        for i in range(0, max(terminology_tables_lengths)):
            newrow = OrderedDict()
            for key, values in terminology_tables.items():
                newrow[key] = values[i] if i < len(values) else ""
            terminology_table.append(newrow)
        terminology_grid = grids.table_to_grid({}, {}, terminology_table)
    else:
        terminology_grid = {}
    terminology_grid["title"] = "Terminology"
    terminology_grid["locked"] = True

    return [
        {"title": "Instructions", "locked": True, "rows": instructions_rows},
        {
            "title": "Dataset",
            "active": True,
            "activeCell": "A2",
            "headers": [assay_headers],
            "rows": [row[0 : len(assay_headers)] for row in rows],
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


def create(name, email, columns=[]):
    if not config.staging:
        return failure("CVDB_STAGING directory is not configured")

    for column in columns:
        if column in config.fields:
            continue
        if column.startswith("obi_") or column.startswith("ontie_"):
            assay_id = column.replace("obi_", "OBI:").replace("ontie_", "ONTIE:")
            root_id = (
                assay_id.replace("_stddev", "")
                .replace("_normalized", "")
                .replace("_qualitative", "")
                .replace("_fold_change", "")
            )
            if assay_id in config.labels:
                continue
            if root_id in config.labels:
                if column.endswith("_stddev"):
                    continue
                if column.endswith("_normalized"):
                    continue
                if column.endswith("_qualitative"):
                    continue
                if column.endswith("_fold_change"):
                    continue
        return failure(f"Unrecognized column '{column}'")

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

    # secret
    try:
        path = os.path.join(config.secret.working_tree_dir, "datasets.tsv")
        datasets = []
        if os.path.isfile(path):
            datasets = tables.read_tsv(path)
        datasets.append(OrderedDict({"ds_id": dataset_id, "submitter_email": email}))
        tables.write_tsv(datasets, path)
    except Exception as e:
        return failure(f"Failed to update '{path}'", {"exception": e})
    try:
        config.secret.index.add([path])
        config.secret.index.commit(
            f"Create dataset {dataset_id}", author=author, committer=config.covic
        )
    except Exception as e:
        return failure(f"Failed to commit '{path}'", {"exception": e})

    # staging
    try:
        dataset_path = os.path.join(datasets_path, str(dataset_id))
        os.mkdir(dataset_path)
    except Exception as e:
        return failure(f"Failed to create '{dataset_path}'", {"exception": e})
    try:
        dataset = {
            "Dataset ID": f"ds:{dataset_id}",
            "Dataset status": "configured",
            "Columns": columns,
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
    table = response["table"]  # remove blank rows

    ab_ids = {}
    for ab in config.read_blinded_antibodies():
        ab_id = ab["ab_id"]
        ab_label = ab_id.replace(":", "-")
        ab_ids[ab_label] = ab_id
    for row in config.ab_controls.values():
        ab_ids[row["label"]] = row["id"]

    assay_headers = get_assay_headers(dataset_id)
    assays = []
    for row in table:
        assay = OrderedDict()
        for header in assay_headers:
            value = header["value"]
            label = header["label"]
            if value == "ab_label":
                row[label] = row[label].strip()
                assay["ab_id"] = ab_ids[row[label]]
            else:
                assay[value] = row[label]
        assays.append(assay)

    author = Actor(name, email)

    # staging
    if not config.staging:
        return failure("CVDB_STAGING directory is not configured")
    dataset_path = os.path.join(config.staging.working_tree_dir, "datasets", str(dataset_id))
    paths = []
    try:
        set_staging_value(dataset_id, "Dataset status", "submitted")
        path = os.path.join(dataset_path, "dataset.yml")
        paths.append(path)
    except Exception as e:
        return failure("Failed to update dataset status", {"exception": e})
    try:
        path = os.path.join(dataset_path, "assays.tsv")
        tables.write_tsv(assays, path)
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

    grid = grids.table_to_grid(config.prefixes, config.fields, table)
    print(f"Submitted assays to dataset {dataset_id}")
    return success({"table": table, "grid": grid, "dataset_id": dataset_id})


def promote(name, email, dataset_id):
    author = Actor(name, email)

    # staging
    if not config.staging:
        return failure("CVDB_STAGING directory is not configured")
    staging_dataset_path = os.path.join(
        config.staging.working_tree_dir, "datasets", str(dataset_id)
    )
    paths = []
    try:
        set_staging_value(dataset_id, "Dataset status", "promoted")
        path = os.path.join(staging_dataset_path, "dataset.yml")
        paths.append(path)
    except Exception as e:
        return failure("Failed to update dataset status", {"exception": e})
    try:
        config.staging.index.add(paths)
        config.staging.index.commit(
            f"Promote dataset {dataset_id}", author=author, committer=config.covic
        )
    except Exception as e:
        return failure(f"Failed to commit '{path}'", {"exception": e})

    # public
    if not config.public:
        return failure("CVDB_PUBLIC directory is not configured")
    public_dataset_path = os.path.join(config.public.working_tree_dir, "datasets", str(dataset_id))
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
    parser.add_argument("dataset", type=str, help="The dataset ID")
    parser.add_argument("output", type=str, help="The output file")
    args = parser.parse_args()

    templates.write_html(args.template, read_data(args.dataset), args.output)
