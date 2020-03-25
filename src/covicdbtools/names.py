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

from collections import OrderedDict

from covicdbtools import tables

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


def split_id(i):
    return i.split(":", maxsplit=1)


def is_id(prefixes, i):
    """Given the prefixes map and an ID string,
    return True if the string starts with a known prefix, False otherwise"""
    if not i:
        return False
    if type(i) is not str:
        return False
    if not ":" in i:
        return False
    prefix, localname = split_id(i)
    return prefix in prefixes


def increment_id(i):
    """Given an ID with some prefix and a localname that is a simple integer (not padded)
    return the next ID."""
    prefix, localname = split_id(i)
    num = int(localname)
    return prefix + ":" + str(num + 1)


def id_to_iri(prefixes, i):
    """Given the prefixes map and an ID string, return an IRI string."""
    prefix, localname = split_id(i)
    if prefix in prefixes:
        return prefixes[prefix] + localname
    return i


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
        labels[row["ID"]] = row["LABEL"]
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
