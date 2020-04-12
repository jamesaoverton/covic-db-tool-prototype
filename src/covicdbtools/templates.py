#!/usr/bin/env python3

import os

from jinja2 import Environment, FileSystemLoader


def render_html(template_path, content):
    """Given a template path and a content dictionary,
    return the HTML string."""
    env = Environment(loader=FileSystemLoader(os.path.dirname(template_path)))
    template = env.get_template(os.path.basename(template_path))
    return template.render(**content)


def write_html(template_path, content, output_path):
    """Given a template path, a content dictionary, and an output path,
    write HTML to the file."""
    with open(output_path, "w") as w:
        w.write(render_html(template_path, content))
