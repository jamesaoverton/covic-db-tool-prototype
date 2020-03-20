#!/usr/bin/env python3

import os

from jinja2 import Environment, FileSystemLoader


def write_html(template_path, content, output_path):
    env = Environment(loader=FileSystemLoader(os.path.dirname(template_path)))
    template = env.get_template(os.path.basename(template_path))

    with open(output_path, "w") as w:
        w.write(template.render(**content))
