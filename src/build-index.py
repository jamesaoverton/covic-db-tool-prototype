#!/usr/bin/env python3

import argparse
import csv
import os
import yaml

from jinja2 import Environment, FileSystemLoader


def write_html(template, output):
    env = Environment(loader=FileSystemLoader(os.path.dirname(template)))
    template = env.get_template(os.path.basename(template))

    with open(output, "w") as w:
        w.write(template.render())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert dataset text files to HTML")
    parser.add_argument("template", type=str, help="The template to use")
    parser.add_argument("output", type=str, help="The output file")
    args = parser.parse_args()

    write_html(args.template, args.output)
