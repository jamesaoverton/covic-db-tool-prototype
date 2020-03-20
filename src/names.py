#!/usr/bin/env python3

import re
import tables

from collections import OrderedDict


def read_prefixes(prefixes_tsv_path):
    prefixes = {}
    for row in tables.read_tsv(prefixes_tsv_path):
        prefixes[row["prefix"]] = row["base"]
    return prefixes


def read_labels(labels_tsv_path):
    id_to_label = {}
    for row in tables.read_tsv(labels_tsv_path):
        id_to_label[row["id"]] = row["label"]
    return id_to_label


def is_id(prefixes, i):
    for prefix in prefixes.keys():
        if i.startswith(prefix + ":"):
            return True
    return False


def id_to_iri(prefixes, i):
    for prefix, base in prefixes.items():
        if i.startswith(prefix + ":"):
            return re.compile("^" + prefix + ":").sub(i, base)
    return i


def id_key_to_label_key(key):
    return re.sub(r"_id$", "_label", key)


def expand_table(id_to_label, odicts):
    """Given the id_to_label map and a list of OrderedDictionaries,
    look for _type_id keys and insert _type_label key-value pairs
    and return that list."""

    table = []
    for row in odicts:
        newrow = OrderedDict()
        for key, value in row.items():
            newrow[key] = value
            if key.endswith("_id") and value in id_to_label:
                label_key = id_key_to_label_key(key)
                newrow[label_key] = id_to_label[value]
        table.append(newrow)
    return table


def expand_tsv(id_to_label, tsv_path):
    """Read a table and then expand it."""
    return expand_table(id_to_label, tables.read_tsv(tsv_path))


def table_to_fields(prefixes, odicts):
    """Given a list of OrderedDictionaries,
    with _id and _label pairs.
    """
    table = []
    for row in odicts:
        newrow = OrderedDict()
        for key, value in row.items():
            if key.endswith("_id"):
                iri = id_to_iri(prefixes, key)
                label = value
                label_key = id_key_to_label_key(key)
                if label_key in row:
                    label = row[label_key]
                newrow[key] = {"iri": iri, "label": label, "value": value}
            elif key.endswith("_label"):
                pass
            else:
                newrow[key] = {"value": value}
        table.append(newrow)
    return table
