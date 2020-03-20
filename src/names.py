#!/usr/bin/env python3

import tables


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
            return i.replace(prefix + ":", base)
    return i
