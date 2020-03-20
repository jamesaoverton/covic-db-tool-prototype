#!/usr/bin/env python3

import argparse
import os
import yaml

import names
import tables
import antibodies
import templates

from collections import OrderedDict


def read_data(prefixes_tsv_path, labels_tsv_path, antibodies_tsv_path, dataset_path):
    prefixes = names.read_prefixes(prefixes_tsv_path)
    id_to_label = names.read_labels(labels_tsv_path)
    ab_list = antibodies.read_antibodies(id_to_label, antibodies_tsv_path)
    ab_map = OrderedDict()
    for ab in ab_list:
        ab_map[ab["ab_id"]] = ab

    for root, dirs, files in os.walk(dataset_path):
        for name in files:
            if name == "assays.tsv":
                assays_tsv_path = os.path.join(root, name)
                for row in tables.read_tsv(assays_tsv_path):
                    if row["Antibody"] in ab_map:
                        for key, value in row.items():
                            if key != "Antibody":
                                ab_map[row["Antibody"]][key] = value

    ab_list = list(ab_map.values())
    return {
        "message": "This is the public view with all antibodies (blinded) and assays.",
        "rows": names.table_to_fields(prefixes, ab_list),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert dataset text files to HTML")
    parser.add_argument("template", type=str, help="The template to use")
    parser.add_argument("prefixes", type=str, help="The prefixes table")
    parser.add_argument("labels", type=str, help="The labels table")
    parser.add_argument("antibodies", type=str, help="The antibodies table")
    parser.add_argument("datasets", type=str, help="The datasets directory")
    parser.add_argument("output", type=str, help="The output file")
    args = parser.parse_args()

    templates.write_html(
        args.template,
        read_data(args.prefixes, args.labels, args.antibodies, args.datasets),
        args.output,
    )