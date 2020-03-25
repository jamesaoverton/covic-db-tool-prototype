#!/usr/bin/env python3
#
# They functions define a "grid", which is a dictionary with "headers" and "rows"
# which are both lists of lists of "cells".
# A "cell" is a dictionary which MUST have a "value" key,
# and MAY have "iri", "label", and other keys.

import json

from collections import OrderedDict
from covicdbtools import names


### Cells
#
# A cell is a dictionary of strings that MUST have a "value" key and "label" key.


def validate_cell(cell):
    if type(cell) is not dict:
        return "Input is not a dictionary"
    if "value" not in cell:
        return "Cell is missing 'value' key"
    if "label" not in cell:
        return "Cell is missing 'label' key"
    return None


def is_cell(cell):
    """Given a cell, return True if is is valid, False otherwise."""
    if validate_cell(cell):
        return False
    return True


def value_cell(value):
    return {"label": value, "value": value}


def value_cells(values):
    cells = []
    for value in values:
        cells.append(value_cell(value))
    return cells


def comment_cell(value, comment):
    cell = value_cell(value)
    cell["comment"] = comment
    return cell


def error_cell(value, comment):
    cell = comment_cell(value, comment)
    cell["status"] = "ERROR"
    return cell


### Grids
#
# A grid is a dictionary that MUST have a "rows" key and MAY have a "headers" key.
# The rows and headers are lists of lists of cells.


def validate_grid(grid):
    if type(grid) is not dict:
        return "Input is not a dictionary"

    if "headers" in grid:
        headers = grid["headers"]
        if type(headers) is not list:
            return "Grid 'headers' is not a list"
        if len(headers) < 1:
            return "Grid 'headers' has no rows"
        for i in range(0, len(headers)):
            row = rows[i]
            if type(row) is not list:
                return "Row {0} is not a list".format(i)
            for j in range(0, len(row)):
                cell = headers[i][j]
                invalid = validate_cell(cell)
                if invalid:
                    return "Cell in 'headers' at row {0} column {1} is not valid: {2}".format(
                        i, j, invalid
                    )

    if "rows" not in grid:
        return "Missing 'rows' key"
    rows = grid["rows"]
    if type(rows) is not list:
        return "Grid 'rows' is not a list"
    if len(rows) < 1:
        return "Grid 'rows' has no rows"
    for i in range(0, len(rows)):
        row = rows[i]
        if type(row) is not list:
            return "Row {0} is not a list".format(i)
        for j in range(0, len(row)):
            cell = rows[i][j]
            invalid = validate_cell(cell)
            if invalid:
                return "Cell in 'rows' at row {0} column {1} is not valid: {2}".format(
                    i, j, invalid
                )

    return None


def is_grid(grid):
    """Given a grid, return True if is is valid, False otherwise."""
    if validate_grid(grid):
        return False
    return True


def table_to_grid(prefixes, fields, table):
    """Given the prefixes map, fields map, and a (probably labelled) table,
    return a grid."""
    grid = {}

    headers = []
    for key in table[0].keys():
        if not (key.endswith("_label") and names.label_key_to_id_key(key) in table[0]):
            label = key
            if key in fields:
                label = fields[key]["label"]
            headers.append({"label": label, "value": key})
    grid["headers"] = [headers]

    rows = []
    for row in table:
        newrow = []
        for key, value in row.items():
            cell = None
            if key.endswith("_id"):
                iri = names.id_to_iri(prefixes, value)
                label = value
                label_key = names.id_key_to_label_key(key)
                if label_key in row and row[label_key] and row[label_key].strip() != "":
                    label = row[label_key]
                cell = {"iri": iri, "label": label, "value": value}
            elif key.endswith("_label") and names.label_key_to_id_key(key) in row:
                pass
            else:
                cell = {"label": value, "value": value}
            if cell:
                newrow.append(cell)
        rows.append(newrow)
    grid["rows"] = rows

    return grid


### HTML Output


def cell_to_html(cell, header=False):
    output = None
    label = None
    if "label" in cell:
        label = cell["label"]
    elif "value" in cell:
        label = cell["value"]

    if "iri" in cell:
        content = """<a href="{0}">{1}</a>""".format(cell["iri"], label)
    else:
        content = label

    classes = []
    if "status" in cell:
        if cell["status"] == "ERROR":
            classes.append("table-danger")

    attrs = ""
    if len(classes) > 0:
        attrs += ' class="{0}"'.format(" ".join(classes))
    if "comment" in cell:
        comment = json.dumps(cell["comment"])  # escape quotes
        attrs += ' data-toggle="popover" data-content={0}'.format(comment)

    if header:
        return "<th{0}>{1}</th>".format(attrs, content)
    else:
        return "<td{0}>{1}</td>".format(attrs, content)


def grid_to_html(grid):
    lines = []
    lines.append("""<table class="table">""")
    if "headers" in grid:
        lines.append("  <thead>")
        for header in grid["headers"]:
            lines.append("    <tr>")
            for cell in header:
                lines.append("      " + cell_to_html(cell, header=True))
            lines.append("    </tr>")
        lines.append("  </thead>")
    if "rows" in grid:
        lines.append("  <tbody>")
        for row in grid["rows"]:
            lines.append("    <tr>")
            for cell in row:
                lines.append("      " + cell_to_html(cell))
            lines.append("    </tr>")
        lines.append("  </tbody>")
    lines.append("</table>")
    return "\n".join(lines)
