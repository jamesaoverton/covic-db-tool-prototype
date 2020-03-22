#!/usr/bin/env python3
#
# In this project a "table" is represented by a list
# of OrderedDicts with the same keys and string values,
# and stored as a TSV file.

import csv
import io

from collections import OrderedDict
from tabulate import tabulate


### Tables


def validate_table(table):
    """Given a table, return None if it is valid,
    otherwise return a message string."""
    if type(table) is not list:
        return "Input is not a list"
    if len(table) < 1:
        return "Table has no rows"
    keys = table[0].keys()
    for i in range(0, len(table)):
        row = table[i]
        if type(row) is not OrderedDict:
            return "Row {0} is not an OrderedDict".format(i)
        if row.keys() != keys:
            return "Keys for row 0 do not match keys for row {0}".format(i)
        for key, value in row.items():
            if type(value) is not str:
                return "In row {0} key '{1}' the value '{2}' is not a string".format(
                    i, key, value
                )
    return None


def is_table(table):
    """Given a table, return True if
    it is a list with length greater than 1
    and all rows are OrderedDicts with the same keys.
    Return False otherwise."""
    if validate_table(table):
        return False
    return True


def test_is_table():
    table = "Foo"
    assert is_table(table) == False

    table = []
    assert is_table(table) == False

    table = [{"foo": "bar"}]
    assert is_table(table) == False

    table = [OrderedDict({"foo": "bar"}), OrderedDict({"zoo": "baz"})]
    assert is_table(table) == False

    table = [OrderedDict({"foo": 1})]
    assert is_table(table) == False

    table = [OrderedDict({"foo": "bar"}), OrderedDict({"foo": "baz"})]
    assert is_table(table) == True


### Reading and Writing


def read_tsv(path):
    """Given a path, read a TSV file
    and return a list of OrderedDicts."""
    with open(path, "r") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def table_to_lists(table):
    """Given a list of OrderedDicts of strings,
    return a list of lists of strings."""
    lists = [list(table[0].keys())]
    for row in table:
        lists.append(list(row.values()))
    return lists


def write_tsv_io(f, table):
    w = csv.writer(f, delimiter="\t", lineterminator="\n")
    w.writerows(table_to_lists(table))


def write_tsv(table, path):
    """Given list of OrderedDicts and a path,
    and return a list of OrderedDicts."""
    with open(path, "w") as f:
        write_tsv_io(f, table)


def table_to_tsv_string(table):
    w = io.StringIO()
    write_tsv_io(w, table)
    return w.getvalue()


def test_tsv_string():
    table = [
        OrderedDict({"foo": "bar", "a": "1"}),
        OrderedDict({"foo": "baz", "a": "2"}),
    ]
    string = """foo	a
bar	1
baz	2
"""
    assert table_to_tsv_string(table) == string


def print_tsv(table):
    lists = table_to_lists(table)
    print(tabulate(lists[1:], lists[0]))
