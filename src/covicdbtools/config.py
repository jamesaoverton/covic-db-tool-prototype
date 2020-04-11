#!/usr/bin/env python3
#
# This module defines global configuration dictionary.
# It can be built from TSV files,
# written to JSON, and loaded from JSON.

import argparse
import json

from covicdbtools import tables


# Global config object.
config = {}


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


### Terms
#
# We have several sheets of terms, which we store by their label.
# These tables always have 'id' and 'label' columns,
# but other columns differ by table.
# We skip the second row, which contains ROBOT template strings.


def read_terms(terms_tsv_path):
    """Read a terms table and return the a dictionary with labels for keys."""
    terms = {}
    for row in tables.read_tsv(terms_tsv_path):
        if row["id"] == "ID":
            continue
        terms[row["label"]] = row
    return terms


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
# The labels map takes ID strings to label strings.


def read_labels(labels_tsv_path):
    """Read the labels table and return the labels map."""
    labels = {}
    for row in tables.read_tsv(labels_tsv_path):
        labels[row["ID"]] = row["LABEL"]
    return labels


### IDs
#
# The ids map takes label strings to ID strings.


def read_ids(labels_tsv_path):
    """Read the labels table and return the IDs map."""
    ids = {}
    for row in tables.read_tsv(labels_tsv_path):
        ids[row["LABEL"]] = row["ID"]
    return ids


### Configuration
#
# A configuration object is just a dictionary with certain keys.


def validate_config(new_config):
    if type(new_config) is not dict:
        return "Config is not a dictionary"
    for key in ["prefixes", "core", "hosts", "isotypes", "assays", "fields", "labels", "ids"]:
        if key not in new_config:
            return f"Config is missing key '{key}'"
    return None


def is_config(new_config):
    if validate_config(new_config):
        return False
    return True

def build_config(prefixes_tsv_path, core_tsv_path, hosts_tsv_path, isotypes_tsv_path, assays_tsv_path, fields_tsv_path, labels_tsv_path):
    new_config = {}
    new_config["prefixes"] = read_prefixes(prefixes_tsv_path)
    new_config["core"] = read_terms(core_tsv_path)
    new_config["hosts"] = read_terms(hosts_tsv_path)
    new_config["isotypes"] = read_terms(isotypes_tsv_path)
    new_config["assays"] = read_terms(assays_tsv_path)
    new_config["fields"] = read_fields(fields_tsv_path)
    new_config["labels"] = read_labels(labels_tsv_path)
    new_config["ids"] = read_ids(labels_tsv_path)
    return new_config


def save_config(new_config, output_path):
    with open(output_path, "w", encoding="utf-8") as output:
        json.dump(new_config, output, ensure_ascii=False, indent=2)


def read_config(config_json_path="config.json"):
    new_config = None
    try:
        with open(config_json_path) as f:
            new_config = json.load(f)
        return new_config
    except Exception as e:
        raise Exception(f"Could not read config from '{config_json_path}': {e}")


def load_config(new_config):
    global config
    config = new_config


def update_config(config_json_path="config.json"):
    new_config = read_config(config_json_path)
    result = validate_config(new_config)
    if result:
        raise Exception(f"Invalid config '{config_json_path}': {result}")
    load_config(new_config)


def main():
    """Read a new configuration from TSV files and save it."""
    parser = argparse.ArgumentParser(description="Read configuration and save it")
    parser.add_argument("prefixes", type=str, help="The prefixes table")
    parser.add_argument("core", type=str, help="The core table")
    parser.add_argument("hosts", type=str, help="The hosts table")
    parser.add_argument("isotypes", type=str, help="The isotypes table")
    parser.add_argument("assays", type=str, help="The assays table")
    parser.add_argument("fields", type=str, help="The fields table")
    parser.add_argument("labels", type=str, help="The labels table")
    parser.add_argument("output", type=str, help="The output JSON file")
    args = parser.parse_args()

    new_config = build_config(args.prefixes, args.core, args.hosts, args.isotypes, args.assays, args.fields, args.labels)
    result = validate_config(new_config)
    if result:
        raise Exception(f"Invalid config: {result}")
    save_config(new_config, args.output)


if __name__ == "__main__":
    main()
