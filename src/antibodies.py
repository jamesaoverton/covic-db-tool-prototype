#!/usr/bin/env python3

import argparse
import os

import names
import tables
import templates

from collections import OrderedDict


def read_antibodies(prefixes, id_to_label, antibodies_tsv_path):
    antibodies = OrderedDict()
    for row in tables.read_tsv(antibodies_tsv_path):
        ab_id = row["ab_id"]
        for key, value in row.items():
            iri = None
            if names.is_id(prefixes, value):
                iri = names.id_to_iri(prefixes, value)
            label = value
            if value in id_to_label:
                # label = value + " " + id_to_label[value]
                label = id_to_label[value]
            row[key] = {"iri": iri, "label": label, "value": value}
        antibodies[ab_id] = row
    return antibodies


def read_data(prefixes_tsv_path, labels_tsv_path, antibodies_tsv_path):
    prefixes = names.read_prefixes(prefixes_tsv_path)
    id_to_label = names.read_labels(labels_tsv_path)
    return {"rows": list(read_antibodies(prefixes, id_to_label, args.antibodies).values())}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert antibodies table to HTML")
    parser.add_argument("template", type=str, help="The template to use")
    parser.add_argument("prefixes", type=str, help="The prefixes table")
    parser.add_argument("labels", type=str, help="The labels table")
    parser.add_argument("antibodies", type=str, help="The antibodies table")
    parser.add_argument("output", type=str, help="The output file")
    args = parser.parse_args()

    templates.write_html(
        args.template,
        read_data(args.prefixes, args.labels, args.antibodies),
        args.output
    )
