#!/usr/bin/env python3
#
# This module defines global configuration dictionary.
# It can be built from TSV files,
# written to JSON, and loaded from JSON.

import argparse
import json
import os

from collections import OrderedDict
from git import Repo
from covicdbtools import tables


# Global config dictionaries.
prefixes = {}
core = {}
hosts = {}
isoforms = {}
assays = {}
fields = {}
labels = {}
ids = {}


# Global git repositories
secret = None
staging = None
public = None


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


def validate(config):
    """Given a config dictionary, return None if it is valid,
    otherwise return a string describing the problem."""
    if not isinstance(config, dict):
        return "Config is not a dictionary"
    for key in [
        "prefixes",
        "core",
        "hosts",
        "isotypes",
        "assays",
        "fields",
        "labels",
        "ids",
    ]:
        if key not in config:
            return f"Config is missing key '{key}'"
    return None


def is_config(config):
    """Given a config dictionary, return True if it is valid, False otherwise."""
    if validate(config):
        return False
    return True


def build(
    prefixes_tsv_path,
    core_tsv_path,
    hosts_tsv_path,
    isotypes_tsv_path,
    assays_tsv_path,
    fields_tsv_path,
    labels_tsv_path,
):
    """Read TSV files and return a new config dictionary."""
    config = {}
    config["prefixes"] = read_prefixes(prefixes_tsv_path)
    config["core"] = read_terms(core_tsv_path)
    config["hosts"] = read_terms(hosts_tsv_path)
    config["isotypes"] = read_terms(isotypes_tsv_path)
    config["assays"] = read_terms(assays_tsv_path)
    config["fields"] = read_fields(fields_tsv_path)
    config["labels"] = read_labels(labels_tsv_path)
    config["ids"] = read_ids(labels_tsv_path)
    return config


def save(config, output_path):
    """Save a config dictionary to a JSON file."""
    with open(output_path, "w", encoding="utf-8") as output:
        json.dump(config, output, ensure_ascii=False, indent=2)


def read(config_json_path="config.json"):
    """Read a config dictionary from a JSON file
    as OrderedDicts."""
    config = None
    try:
        with open(config_json_path) as f:
            config = json.load(f, object_pairs_hook=OrderedDict)
        return config
    except Exception as e:
        raise Exception(f"Could not read config from '{config_json_path}': {e}")


def load(config):
    """Load a new config into the global dictionaries."""
    global prefixes, core, hosts, isotypes, assays, fields, labels, ids
    prefixes = config["prefixes"]
    core = config["core"]
    hosts = config["hosts"]
    isotypes = config["isotypes"]
    assays = config["assays"]
    fields = config["fields"]
    labels = config["labels"]
    ids = config["ids"]


def update(config_json_path=None):
    """Read and load a config."""
    if not config_json_path:
        config_json_path = os.path.join(os.path.dirname(__file__), "config.json")
    config = read(config_json_path)
    result = validate(config)
    if result:
        raise Exception(f"Invalid config '{config_json_path}': {result}")
    load(config)


def init():
    """Set the global data repositories."""
    global secret, staging, public
    if "CVDB_DATA" in os.environ:
        data_path = os.environ["CVDB_DATA"]
        if os.path.isdir(data_path):
            secret = Repo(os.path.join(data_path, "secret"))
            staging = Repo(os.path.join(data_path, "staging"))
            public = Repo(os.path.join(data_path, "public"))
    update()


def initialize():
    """Create the global data repositories."""
    if "CVDB_DATA" in os.environ:
        data_path = os.environ["CVDB_DATA"]
        os.mkdir(data_path)
        for name in ["secret", "staging", "public"]:
            path = os.path.join(data_path, name)
            Repo.init(path, mkdir=True)
        init()
        print(f"Initialized data repositories in '{data_path}'")
    else:
        raise Exception("ERROR: Please set the CVDB_DATA environment variable")


def main():
    """Read a new configuration from TSV files and save it as JSON."""
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

    config = build(
        args.prefixes,
        args.core,
        args.hosts,
        args.isotypes,
        args.assays,
        args.fields,
        args.labels,
    )
    result = validate(config)
    if result:
        raise Exception(f"Invalid config: {result}")
    save(config, args.output)


# Load config.json and data repositories
init()


if __name__ == "__main__":
    main()
