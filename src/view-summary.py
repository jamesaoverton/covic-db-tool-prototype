#!/usr/bin/env python3

import argparse
import os
import yaml

import names
import tables

from collections import OrderedDict
from jinja2 import Environment, FileSystemLoader


def read_data(prefixes_tsv_path, labels_tsv_path, antibodies_tsv_path, dataset_path):
    prefixes = names.read_prefixes(prefixes_tsv_path)
    id_to_label = names.read_labels(labels_tsv_path)

    antibodies = OrderedDict()
    for row in tables.read_tsv(antibodies_tsv_path):
        ab_id = row["ab_id"]
        for key, value in row.items():
            iri = None
            if names.is_id(prefixes, value):
                iri = names.id_to_iri(prefixes, value)
            label = value
            if value in id_to_label:
                #label = value + " " + id_to_label[value]
                label = id_to_label[value]
            row[key] = {"iri": iri, "label": label, "value": value}
        antibodies[ab_id] = row

    for root, dirs, files in os.walk(dataset_path):
        for name in files:
            if name == "assays.tsv":
                assays_tsv_path = os.path.join(root, name)
                for row in tables.read_tsv(assays_tsv_path):
                    if row["Antibody"] in antibodies:
                        for key, value in row.items():
                            if key != "Antibody":
                                antibodies[row["Antibody"]][key] = {"label": value}

    return list(antibodies.values())


def write_html(rows, template, output):
    env = Environment(loader=FileSystemLoader(os.path.dirname(template)))
    template = env.get_template(os.path.basename(template))

    with open(output, "w") as w:
        w.write(template.render(rows=rows))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert dataset text files to HTML")
    parser.add_argument("template", type=str, help="The template to use")
    parser.add_argument("prefixes", type=str, help="The prefixes table")
    parser.add_argument("labels", type=str, help="The labels table")
    parser.add_argument("antibodies", type=str, help="The antibodies table")
    parser.add_argument("datasets", type=str, help="The datasets directory")
    parser.add_argument("output", type=str, help="The output file")
    args = parser.parse_args()

    write_html(read_data(args.prefixes, args.labels, args.antibodies, args.datasets), args.template, args.output)
