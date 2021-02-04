#!/usr/bin/env python3
#
# This module defines global configuration dictionary.
# It can be built from TSV files,
# written to JSON, and loaded from JSON.

import argparse
import json
import os

from collections import OrderedDict
from git import Actor, Repo
from covicdbtools import tables


# Global config dictionaries.
fields = {}
prefixes = {}
core = {}
hosts = {}
isoforms = {}
light_chains = {}
heavy_chain_germline = {}
assays = {}
parameters = {}
qualitative_measures = {}
death_reason = {}
animal_model_strain = {}
labels = {}
ids = {}


# Global git repositories
secret = None
staging = None
public = None
covic = Actor("CoVIC", "covic@lji.org")


# # Fields
#
# A field describes a column of that may occur in multiple tables,
# and its SQL name, human friendly label, and eventually validation rules.
# The fields map takes column names to dictionaries.


def read_fields(fields_tsv_path):
    """Read the fields table and return the fields map."""
    fields = {}
    for row in tables.read_tsv(fields_tsv_path):
        fields[row["field"]] = {k: v for k, v in row.items() if v is not None and v.strip() != ""}
    return fields


# # Prefixes
#
# The prefixes map takes short prefixes to long base URLs.
# We can then convert IDs (CURIES) to IRIs (URIs).


def read_prefixes(prefixes_tsv_path):
    """Read the prefixes table and return the prefixes map."""
    prefixes = {}
    for row in tables.read_tsv(prefixes_tsv_path):
        prefixes[row["prefix"]] = row["base"]
    return prefixes


# # Terms
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
        if "notes" in row:
            del row["notes"]
        terms[row["label"]] = row
    return terms


# # Labels
#
# The labels map takes ID strings to label strings.


def read_labels(labels_tsv_path):
    """Read the labels table and return the labels map."""
    labels = {}
    for row in tables.read_tsv(labels_tsv_path):
        id = row["ID"]
        if id in labels:
            raise Exception(f"Duplicate ID {id}")
        labels[id] = row["LABEL"]
    return labels


# # IDs
#
# The ids map takes label strings to ID strings.


def read_ids(labels_tsv_path):
    """Read the labels table and return the IDs map."""
    ids = {}
    for row in tables.read_tsv(labels_tsv_path):
        label = row["LABEL"]
        if label in ids:
            raise Exception("Duplicate label '{label}'")
        ids[label] = row["ID"]
    return ids


# # Antibodies
#
# Read the table of blinded antibodies from Staging.


def read_blinded_antibodies():
    "Return a list of dicts of blinded antibodies"
    if not staging:
        raise Exception("CVDB_STAGING directory is not configured")
    blind = []
    path = os.path.join(staging.working_tree_dir, "antibodies.tsv")
    if os.path.isfile(path):
        blind = tables.read_tsv(path)
    return blind


# # Configuration
#
# A configuration object is just a dictionary with certain keys.


def validate(config):
    """Given a config dictionary, return None if it is valid,
    otherwise return a string describing the problem."""
    if not isinstance(config, dict):
        return "Config is not a dictionary"
    for key in [
        "fields",
        "prefixes",
        "core",
        "hosts",
        "isotypes",
        "assays",
        "parameters",
        "qualitative_measures",
        "death_reason",
        "animal_model_strain",
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
    fields_tsv_path,
    core_tsv_path,
    hosts_tsv_path,
    isotypes_tsv_path,
    light_chain_tsv_path,
    heavy_chain_germline_tsv_path,
    assays_tsv_path,
    parameters_tsv_path,
    qualitative_measures_tsv_path,
    death_reason_tsv_path,
    animal_model_strain_tsv_path,
    labels_tsv_path,
):
    """Read TSV files and return a new config dictionary."""
    config = {}
    config["prefixes"] = read_prefixes(prefixes_tsv_path)
    config["fields"] = read_fields(fields_tsv_path)
    config["core"] = read_terms(core_tsv_path)
    config["hosts"] = read_terms(hosts_tsv_path)
    config["isotypes"] = read_terms(isotypes_tsv_path)
    config["light_chains"] = read_terms(light_chain_tsv_path)
    config["heavy_chain_germline"] = read_terms(heavy_chain_germline_tsv_path)
    config["assays"] = read_terms(assays_tsv_path)
    config["parameters"] = read_terms(parameters_tsv_path)
    config["qualitative_measures"] = read_terms(qualitative_measures_tsv_path)
    config["death_reason"] = read_terms(death_reason_tsv_path)
    config["animal_model_strain"] = read_terms(animal_model_strain_tsv_path)
    config["labels"] = read_labels(labels_tsv_path)
    config["ids"] = read_ids(labels_tsv_path)

    # Check for duplicates
    term_sets = [
        "core",
        "hosts",
        "isotypes",
        "light_chains",
        "heavy_chain_germline",
        "assays",
        "parameters",
        "qualitative_measures",
        "death_reason",
        "animal_model_strain",
    ]
    ids = set()
    labels = set()
    for term_set in term_sets:
        terms = config[term_set]
        for label, term in terms.items():
            id = term["id"]
            if id in ids:
                raise Exception(f"Duplicate ID '{id}' in term set '{term_set}'")
            if label in labels:
                raise Exception(f"Duplicate label '{label}' in term set '{term_set}'")
            ids.add(id)
            labels.add(label)

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
    global prefixes, core, hosts, isotypes, light_chains, heavy_chain_germline
    global assays, parameters, qualitative_measures, death_reason, animal_model_strain
    global fields, labels, ids
    prefixes = config["prefixes"]
    core = config["core"]
    hosts = config["hosts"]
    isotypes = config["isotypes"]
    light_chains = config["light_chains"]
    heavy_chain_germline = config["heavy_chain_germline"]
    assays = config["assays"]
    parameters = config["parameters"]
    qualitative_measures = config["qualitative_measures"]
    death_reason = config["death_reason"]
    animal_model_strain = config["animal_model_strain"]
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
    parser.add_argument("prefix", type=str, help="The prefix table")
    parser.add_argument("field", type=str, help="The field table")
    parser.add_argument("core", type=str, help="The core table")
    parser.add_argument("host", type=str, help="The host table")
    parser.add_argument("isotype", type=str, help="The isotype table")
    parser.add_argument("light_chain", type=str, help="The light_chain table")
    parser.add_argument("heavy_chain_germline", type=str, help="The heavy_chain_germline table")
    parser.add_argument("assay", type=str, help="The assay table")
    parser.add_argument("parameter", type=str, help="The parameter table")
    parser.add_argument("qualitative_measure", type=str, help="The qualitative_measure table")
    parser.add_argument("death_reason", type=str, help="The death_reason table")
    parser.add_argument("animal_model_strain", type=str, help="The animal_model_strain table")
    parser.add_argument("label", type=str, help="The label table")
    parser.add_argument("output", type=str, help="The output JSON file")
    args = parser.parse_args()

    config = build(
        args.prefix,
        args.field,
        args.core,
        args.host,
        args.isotype,
        args.light_chain,
        args.heavy_chain_germline,
        args.assay,
        args.parameter,
        args.qualitative_measure,
        args.death_reason,
        args.animal_model_strain,
        args.label,
    )
    result = validate(config)
    if result:
        raise Exception(f"Invalid config: {result}")
    save(config, args.output)


if __name__ == "__main__":
    main()
else:
    # Load config.json and data repositories
    init()
