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


# # Inputs
#
# A "source" can be:
# - a table: list of OrderedDicts
# - a response with a "table"
# - a Django request_files object: with a single .xlsx file
# - a path to a TSV or Excel file
# - a TSV or Excel file
#
# A "datatype" can be:
# - "antibodies"
# - an assay type name or ID
# - a dataset ID: integer

# # Outputs
#
# Almost all of these functions return a response dictionary,
# see `responses.py` for details.
#


def initialize():
    """Create the global data repositories."""
    config.initialize()
    return success()


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


def read(source, sheet=None):
    """Read a source and return a response with a "table" key."""
    if tables.is_table(source):
        return success({"table": source})
    if responses.is_response(source):
        if "table" in source:
            return success({"table": source["table"]})
        else:
            return failure(f"Response does not have 'table': '{source}'")
    if isinstance(source, str) or hasattr(source, "read"):
        return read_path(source, sheet)
    if requests.is_request(source):
        response = requests.read_file(source)
        if failed(response):
            return response
        table = workbooks.read(response["content"], sheet)
        return success({"table": table})
    raise Exception(f"Unknown input '{source}'")


def convert(source, destination):
    """Given a source and a destimation (format or path)
    convert the table to that format
    and return a response with a "content" key."""
    table = None
    grid = None

    if grids.is_grid(source):
        grid = source
    else:
        response = read(source)
        if failed(response):
            return response
        table = response["table"]

    output_format = destination.lower()
    if output_format not in ["tsv", "html"]:
        filename, extension = os.path.splitext(destination)
        output_format = extension.lower().lstrip(".")
    if output_format.lower() == "tsv":
        content = tables.table_to_tsv_string(table)
        return success({"table": table, "content type": responses.tsv, "content": content})
    elif output_format.lower() == "html":
        if not grid:
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
        return failure(f"Unsupported output format for '{destination}'")


def expand(source, sheet=None):
    """Given a table, return a response in which "table" is the expanded form."""
    response = read(source, sheet)
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


def fill(datatype, source=None):
    """Given a datatype string and an optional table of data,
    fill the template for the given datatype,
    and return a response with "grids"."""
    if source:
        response = read(source)
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


def fetch_template(datatype):
    """Fetch the template for a given datatype."""
    return fill_rows(datatype)


def validate(datatype, source):
    """Given a datatype and a source,
    validate it and return a response with "grid" and maybe "errors",
    and an Excel file as "content"."""
    if datatype == "antibodies":
        sheet = "Antibodies"
    else:
        sheet = "Dataset"
    response = read(source, sheet)
    if failed(response):
        return response

    table = response["table"]
    if datatype == "antibodies":
        return antibodies.validate(table)
    else:
        return datasets.validate(datatype, table)


def create_dataset(name, email, columns=[]):
    """Given the submitter's name, email, and an assay_type, create a dataset.
    The response will have a "dataset" key with the new id."""
    return datasets.create(name, email, columns=columns)


def submit_antibodies(name, email, organization, source):
    """Given the submitter's name, email, organization, and a source
    validate and submit a set of antibodies.
    A successful response will include a table of submitted data and IDs."""
    response = validate("antibodies", source)
    if failed(response):
        return response
    table = response["table"]
    return antibodies.submit(name, email, organization, table)


def submit_assays(name, email, dataset_id, source):
    """Given the submitter's name and email, an existing dataset ID, and a source
    validate it and submit a set of assays.
    A successful response will include a table of submitted data."""
    response = validate(dataset_id, source)
    if failed(response):
        return response
    table = response["table"]
    return datasets.submit(name, email, dataset_id, table)


def promote_dataset(name, email, dataset_id):
    """Given a user name, email, and a dataset ID,
    promote the dataset from staging to production."""
    return datasets.promote(name, email, dataset_id)
