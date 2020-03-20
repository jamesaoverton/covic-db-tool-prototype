#!/usr/bin/env python3

import argparse
import os

import tables
import names
import templates


def read_antibodies(id_to_label, antibodies_tsv_path):
    return names.expand_tsv(id_to_label, antibodies_tsv_path)


def read_data(prefixes_tsv_path, labels_tsv_path, antibodies_tsv_path):
    prefixes = names.read_prefixes(prefixes_tsv_path)
    id_to_label = names.read_labels(labels_tsv_path)
    antibodies = read_antibodies(id_to_label, antibodies_tsv_path)
    return {
        "message": "These are all the antibodies in the system.",
        "rows": names.table_to_fields(prefixes, antibodies),
    }


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
        args.output,
    )
