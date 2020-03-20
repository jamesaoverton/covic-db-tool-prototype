#!/usr/bin/env python3

import argparse
import os
import yaml

import names
import tables

from jinja2 import Environment, FileSystemLoader


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


def read_data(prefixes_tsv_path, labels_tsv_path, dataset_path):
    prefixes = names.read_prefixes(prefixes_tsv_path)
    id_to_label = names.read_labels(labels_tsv_path)

    dataset_yaml_path = os.path.join(dataset_path, "dataset.yml")
    with open(dataset_yaml_path, "r") as f:
        dataset = yaml.load(f, Loader=yaml.SafeLoader)

    fields = []
    for key, value in dataset.items():
        iri = None
        if names.is_id(prefixes, value):
            iri = names.id_to_iri(prefixes, value)
        label = value
        if value in id_to_label:
            label = value + " " + id_to_label[value]
        fields.append({"field": key, "iri": iri, "label": label, "value": value})

    assays_tsv_path = os.path.join(dataset_path, "assays.tsv")
    assays = []
    for row in tables.read_tsv(assays_tsv_path):
        assays.append(row)

    return {"dataset": dataset, "fields": fields, "assays": assays}


def write_html(data, template, output):
    env = Environment(loader=FileSystemLoader(os.path.dirname(template)))
    template = env.get_template(os.path.basename(template))

    with open(output, "w") as w:
        w.write(template.render(data=data))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert dataset text files to HTML")
    parser.add_argument("template", type=str, help="The template to use")
    parser.add_argument("prefixes", type=str, help="The prefixes table")
    parser.add_argument("labels", type=str, help="The labels table")
    parser.add_argument("dataset", type=str, help="The dataset directory")
    parser.add_argument("output", type=str, help="The output file")
    args = parser.parse_args()

    write_html(read_data(args.prefixes, args.labels, args.dataset), args.template, args.output)
