#!/usr/bin/env python3
#
# These functions handle prefixes, labels, and IRIs.
# They also distinguish "concise tables" which do not have _label columns
# from "labelled tables" for which each _id column is followed by a _label column.
# They also define a "grid", which is a dictionary with "headers" and "rows"
# which are both lists of lists of "cells".
# A "cell" is a dictionary which MUST have a "value" key,
# and MAY have "iri", "label", and other keys.

import re
import tables

from collections import OrderedDict


### Prefixes
#
# The prefixes map takes short prefixes to long base URLs.
# We can then convert IDs (CURIES) to IRIs (URIs).


def read_prefixes(prefixes_tsv_path):
    """Read the prefixes table and return the prefixes map."""
    prefixes = {}
    for row in tables.read_tsv(prefixes_tsv_path):
        prefixes[row["prefix"]] = row["base"]
    return prefixes


def is_id(prefixes, i):
    """Given the prefixes map and an ID string,
    return True if the string starts with a known prefix, False otherwise"""
    for prefix in prefixes.keys():
        if i.startswith(prefix + ":"):
            return True
    return False


def id_to_iri(prefixes, i):
    """Given the prefixes map and an ID string, return an IRI string."""
    for prefix, base in prefixes.items():
        if i.startswith(prefix + ":"):
            return re.compile("^" + prefix + ":").sub(base, i)
    return i


def test_prefixes():
    prefixes = {"ex": "http://example.com/"}
    assert id_to_iri(prefixes, "ex:bar") == "http://example.com/bar"


### Fields
#
# A field describes a column of that may occur in multiple tables,
# and its SQL name, human friendly label, and eventually validation rules.
# The fields map takes column names to dictionaries.


def read_fields(fields_tsv_path):
    """Read the fields table and return the fields map."""
    fields = {}
    for row in tables.read_tsv(fields_tsv_path):
        fields[row["field"]] = row
    return fields


### Labels
#
# The labels map takes IDs to label strings.


def read_labels(labels_tsv_path):
    """Read the labels table and return the labels map."""
    labels = {}
    for row in tables.read_tsv(labels_tsv_path):
        labels[row["id"]] = row["label"]
    return labels


### Concise Tables
#
# A concise table is a table that does not have any _label columns.


def validate_concise_table(concise_table):
    """Given a concise table, return None if it is valid,
    otherwise return a message string."""
    invalid = tables.validate_table(concise_table)
    if invalid:
        return invalid
    for row in concise_table:
        for key in row.keys():
            if key.endswith("_label"):
                return "Key {0} not allowed in concise table".format(key)
    return None


def is_concise_table(concise_table):
    """Given a concise table, return True if is is valid, False otherwise."""
    if validate_concise_table(concise_table):
        return False
    return True


def test_concise_table():
    table = [OrderedDict({"foo": "bar"})]
    assert is_concise_table(table) == True

    table = [OrderedDict({"foo_id": "bar"})]
    assert is_concise_table(table) == True

    table = [OrderedDict({"foo_label": "bar"})]
    assert is_concise_table(table) == False


### Labelled Tables
#
# A labelled table is a tabel that has a _label column following each _id column.


def id_key_to_label_key(key):
    """Given a key string, replace terminal _id with _label."""
    return re.sub(r"_id$", "_label", key)


def label_key_to_id_key(key):
    """Given a key string, replace terminal _label with _id."""
    return re.sub(r"_label$", "_id", key)


def validate_labelled_table(labelled_table):
    """Given a labelled table, return None if it is valid,
    otherwise return a message string."""
    invalid = tables.validate_table(labelled_table)
    if invalid:
        return invalid
    keys = labelled_table[0].keys()
    for key in keys:
        id_key = label_key_to_id_key(key)
        label_key = id_key_to_label_key(key)
        if key.endswith("_id") and label_key not in keys:
            return "ID key {0} does not have corresponding label key {1}".format(
                key, label_key
            )
        elif key.endswith("_label") and id_key not in keys:
            return "Label key {0} does not have corresponding id key {1}".format(
                key, id_key
            )
    return None


def is_labelled_table(labelled_table):
    """Given a labelled table, return True if is is valid, False otherwise."""
    if validate_labelled_table(labelled_table):
        return False
    return True


def label_table(labels, table):
    """Given the labels map and a table,
    look for _id keys and insert _label key-value pairs
    then return the new table."""
    newtable = []
    for row in table:
        newrow = OrderedDict()
        for key, value in row.items():
            newrow[key] = value
            label_key = id_key_to_label_key(key)
            if key.endswith("_id") and label_key not in row.keys():
                if value in labels:
                    newrow[label_key] = labels[value]
                else:
                    newrow[label_key] = ""
        newtable.append(newrow)
    return newtable


def label_tsv(labels, tsv_path):
    """Read a TSV table and then label it."""
    return label_table(labels, tables.read_tsv(tsv_path))


def unlabel_table(table):
    """Given a table, remove all _label key-value pairs."""
    for row in table:
        for key in row.keys():
            if key.endswith("label"):
                del row[key]
    return table


def test_labelled_table():
    table = [OrderedDict({"foo": "bar"})]
    assert is_labelled_table(table) == True

    table = [OrderedDict({"foo_id": "bar"})]
    assert is_labelled_table(table) == False

    table = [OrderedDict({"foo_id": "bar", "foo_label": "Bar"})]
    assert is_labelled_table(table) == True

    labels = {"bar": "Bar"}
    concise_table = [OrderedDict({"foo_id": "bar"})]
    labelled_table = [OrderedDict({"foo_id": "bar", "foo_label": "Bar"})]
    assert label_table(labels, concise_table) == labelled_table
    assert unlabel_table(labelled_table) == concise_table


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
        if not key.endswith("_label"):
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
                iri = id_to_iri(prefixes, value)
                label = value
                label_key = id_key_to_label_key(key)
                if label_key in row and row[label_key] and row[label_key].strip() != "":
                    label = row[label_key]
                cell = {"iri": iri, "label": label, "value": value}
            elif key.endswith("_label"):
                pass
            else:
                cell = {"label": value, "value": value}
            if cell:
                newrow.append(cell)
        rows.append(newrow)
    grid["rows"] = rows

    return grid


def test_grid():
    grid = "Foo"
    assert is_grid(grid) == False

    grid = {}
    assert is_grid(grid) == False

    grid = {"rows": {}}
    assert is_grid(grid) == False

    grid = {"rows": []}
    assert is_grid(grid) == False

    grid = {"rows": ["Foo"]}
    assert is_grid(grid) == False

    grid = {"rows": [{"value": "foo"}]}
    assert is_grid(grid) == False

    grid = {"headers": "Foo", "rows": ["Foo"]}
    assert is_grid(grid) == False

    prefixes = {"ex": "http://example.com/"}
    fields = {"foo_id": {"label": "Foo"}}
    labelled_table = [OrderedDict({"foo_id": "ex:bar", "foo_label": "Bar"})]
    grid = {
        "headers": [[{"label": "Foo", "value": "foo_id"}]],
        "rows": [
            [{"iri": "http://example.com/bar", "label": "Bar", "value": "ex:bar"}]
        ],
    }
    assert table_to_grid(prefixes, fields, labelled_table) == grid
