#!/usr/bin/env python3

import argparse
import os
import yaml

from collections import OrderedDict

from covicdbtools import names, tables, grids, templates, antibodies


def read_data(
    prefixes_tsv_path,
    fields_tsv_path,
    labels_tsv_path,
    antibodies_tsv_path,
    dataset_path,
):
    prefixes = names.read_prefixes(prefixes_tsv_path)
    fields = names.read_fields(fields_tsv_path)
    labels = names.read_labels(labels_tsv_path)

    # ab_list = antibodies.read_antibodies(labels, antibodies_tsv_path)
    ab_table = tables.read_tsv(antibodies_tsv_path)
    ab_map = OrderedDict()
    for ab in ab_table:
        ab_map[ab["ab_label"]] = ab

    for root, dirs, files in os.walk(dataset_path):
        for name in files:
            if name.startswith("antibodies"):
                continue
            if name.endswith("-valid-expanded.tsv"):
                assays_tsv_path = os.path.join(root, name)
                assay_name = name.replace("-submission-valid-expanded.tsv", "")
                table = tables.read_tsv(assays_tsv_path)

                # Add these keys to all rows, preserving order.
                keys = table[0].keys()
                for ab in ab_map.values():
                    for key in keys:
                        if key != "ab_label":
                            newkey = assay_name + "_" + key
                            ab[newkey] = ""

                for row in table:
                    if row["ab_label"] in ab_map:
                        for key, value in row.items():
                            if key != "ab_label":
                                newkey = assay_name + "_" + key
                                ab_map[row["ab_label"]][newkey] = value

    ab_list = list(ab_map.values())
    grid = grids.table_to_grid(prefixes, fields, ab_list)
    grid["message"]: "This is the public view with all antibodies (blinded) and assays."
    return grid


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert dataset text files to HTML")
    parser.add_argument("template", type=str, help="The template to use")
    parser.add_argument("prefixes", type=str, help="The prefixes table")
    parser.add_argument("fields", type=str, help="The fields table")
    parser.add_argument("labels", type=str, help="The labels table")
    parser.add_argument("antibodies", type=str, help="The antibodies table")
    parser.add_argument("datasets", type=str, help="The datasets directory")
    parser.add_argument("output", type=str, help="The output file")
    args = parser.parse_args()

    templates.write_html(
        args.template,
        read_data(
            args.prefixes, args.fields, args.labels, args.antibodies, args.datasets
        ),
        args.output,
    )
