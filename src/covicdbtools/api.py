#!/usr/bin/env python

import os

from io import BytesIO
from covicdbtools import (
    config,
    names,
    tables,
    grids,
    workbooks,
    templates,
    antibodies,
    datasets,
    requests,
    responses,
)
from covicdbtools.responses import success, failure, failed


def find_assay_type_id(assay_name):
    """Given the name of an assay type, return its ID."""
    assay_name = assay_name.replace("-", " ")
    if assay_name in config.assays:
        return config.assays[assay_name]["id"]
    return None


def read_path(path, sheet=None):
    """Read a TSV or Excel from a path and return a response with a "table" key."""
    table = None
    filename, extension = os.path.splitext(path)
    extension = extension.lower()
    if extension == ".xlsx":
        table = workbooks.read(path, sheet)
    elif extension == ".tsv":
        table = tables.read_tsv(path)
    else:
        return failure(f"Unsupported input format for '{path}'")
    return success({"table": table})


def read(table_or_path, sheet=None):
    """Read a table and return a response with a "table" key."""
    if tables.is_table(table_or_path):
        return success({"table": table_or_path})
    if grids.is_grid(table_or_path):
        return success({"grid": table_or_path})
    if isinstance(table_or_path, str) or hasattr(table_or_path, "read"):
        return read_path(table_or_path, sheet)
    return failure(f"Unknown input '{table_or_path}'")


def convert(table_or_path, output_format_or_path):
    """Given a table and an output format or path,
    convert the table to that format
    and return a response with a "content" key."""
    response = read(table_or_path)
    if failed(response):
        return response

    output_format = output_format_or_path.lower()
    if output_format not in ["tsv", "html"]:
        filename, extension = os.path.splitext(output_format_or_path)
        output_format = extension.lower().lstrip(".")
    if output_format.lower() == "tsv":
        table = response["table"]
        content = tables.table_to_tsv_string(table)
        return success(
            {"table": table, "content type": responses.tsv, "content": content,}
        )
    elif output_format.lower() == "html":
        table = None
        grid = None
        if "grid" in response:
            grid = response["grid"]
        elif "table" in response:
            table = response["table"]
            grid = grids.table_to_grid(config.prefixes, config.fields, table)
        html = grids.grid_to_html(grid)
        content = templates.render_html("templates/grid.html", {"html": html})
        return success(
            {
                "table": table,
                "grid": grid,
                "html": html,
                "content type": responses.html,
                "content": content,
            }
        )
    else:
        return failure(f"Unsupported output format for '{output_format_or_path}'")


def expand(table_or_path, sheet=None):
    """Given a table, return a response in which "table" is the expanded form."""
    response = read(table_or_path, sheet)
    if failed(response):
        return response
    table = response["table"]
    return success({"table": names.label_table(config.labels, table)})


def fill_rows(datatype, rows=[]):
    """Given a datatype string and optional rows list,
    fill the template for the given datatype,
    and return a response with "grids"."""
    grids = None
    if datatype.lower() == "antibodies":
        grids = antibodies.fill(rows)
    else:
        grids = datasets.fill(datatype, rows)

    content = BytesIO()
    workbooks.write(grids, content)
    return success({"grids": grids, "content type": responses.xlsx, "content": content})


def fill(datatype, table_or_path=None):
    """Given a datatype string and an optional table of data,
    fill the template for the given datatype,
    and return a response with "grids"."""
    if table_or_path:
        response = read(table_or_path)
        if failed(response):
            return response
        table = response["table"]
        grid = grids.table_to_grid(config.prefixes, config.fields, table)
        response = fill_rows(datatype, grid["rows"])
        response["table"] = table
        response["grid"] = grid
    else:
        response = fill_rows(datatype)
    return response


def validate(datatype, table_or_path):
    """Given a datatype and a table or path, return a validation response."""
    if datatype == "antibodies":
        sheet = "Antibodies"
    else:
        sheet = "Dataset"
    response = read(table_or_path, sheet)
    if failed(response):
        return response

    table = response["table"]
    if datatype == "antibodies":
        return antibodies.validate(table)
    else:
        return datasets.validate(datatype, table)


def validate_request(datatype, request_files):
    """Given a datatype and a request object, return a validation response."""
    response = requests.read_file(request_files)
    if failed(response):
        return response

    if datatype == "antibodies":
        sheet = "Antibodies"
    else:
        sheet = "Dataset"
    table = workbooks.read(response["content"], sheet)
    return validate(datatype, table)


def create(author, dataset_config):
    pass


def store(author, dataset_id, table):
    if dataset_id == "antibodies":
        return antibodies.store(table)

    return failure(f"Unrecognized dataset ID {dataset_id}")


def submit(name, email, dataset_id, table_or_path):
    if dataset_id == "antibodies":
        response = validate(dataset_id, table_or_path)
        if failed(response):
            return response
        table = response["table"]
        return antibodies.submit(name, email, table)

    return failure(f"Unrecognized dataset ID {dataset_id}")


def promote(author, dataset_id):
    pass
