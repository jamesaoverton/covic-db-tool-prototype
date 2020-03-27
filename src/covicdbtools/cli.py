#!/usr/bin/env python

import argparse
import os

from covicdbtools import (
    names,
    tables,
    grids,
    workbooks,
    templates,
    antibodies,
    datasets,
    submissions,
)

prefixes = names.read_prefixes("ontology/prefixes.tsv")
labels = names.read_labels("build/labels.tsv")
fields = names.read_fields("ontology/fields.tsv")


def find_assay_type_id(path):
    root, ext = os.path.splitext(path)
    filename = os.path.basename(root)
    assay_name = (
        filename.replace("-submission", "")
        .replace("-valid", "")
        .replace("-invalid", "")
        .replace("-highlighted", "")
        .replace("-", " ")
    )
    for key, value in datasets.assay_type_labels.items():
        if assay_name == value:
            return key
    raise Exception(
        "Unrecognized assay name '{0}' for path '{1}'".format(assay_name, path)
    )


def read(args):
    table = None
    if args.input.endswith(".xlsx"):
        table = workbooks.read_xlsx(args.input, args.sheet)
    elif args.input.endswith(".tsv"):
        table = tables.read_tsv(args.input)
    else:
        raise Exception("Unsupported input format for '{0}'".format(args.input))
    tables.print_tsv(table)


def expand(args):
    table = None
    if args.input.endswith(".xlsx"):
        table = workbooks.read_xlsx(args.input, args.sheet)
    elif args.input.endswith(".tsv"):
        table = tables.read_tsv(args.input)
    else:
        raise Exception("Unsupported input format for '{0}'".format(args.input))

    table = names.label_table(labels, table)

    if args.output.endswith(".tsv"):
        tables.write_tsv(table, args.output)
    elif args.output.endswith(".html"):
        grid = grids.table_to_grid(prefixes, fields, table)
        html = grids.grid_to_html(grid)
        templates.write_html("templates/grid.html", {"html": html}, args.output)
    else:
        raise Exception("Unsupported output format for '{0}'".format(args.output))


def fill(args):
    if "antibodies-submission" in args.output:
        table = tables.read_tsv(args.input)
        grid = grids.table_to_grid(prefixes, fields, table)
        antibodies.write_xlsx(args.output, grid["rows"])
    else:
        table = tables.read_tsv(args.input)
        grid = grids.table_to_grid(prefixes, fields, table)
        datasets.write_xlsx(args.output, find_assay_type_id(args.input), grid["rows"])


def update(args):
    if "antibodies-submission" in args.output:
        antibodies.write_xlsx(args.output)
    else:
        datasets.write_xlsx(args.output, find_assay_type_id(args.output))


def validate(args):
    table = None
    grid = None
    if args.input.endswith(".xlsx"):
        if "antibodies-submission" in args.output:
            table = workbooks.read_xlsx(args.input, "Antibodies")
            grid = antibodies.validate_submission(table)
        else:
            table = workbooks.read_xlsx(args.input, "Dataset")
            grid = datasets.validate_submission(find_assay_type_id(args.input), table)
    elif args.input.endswith(".tsv"):
        table = tables.read_tsv(args.input)
        if "antibodies-submission" in args.output:
            grid = antibodies.validate_submission(table)
        else:
            grid = datasets.validate_submission(find_assay_type_id(args.input), table)
    else:
        raise Exception("Unsupported input format for '{0}'".format(args.input))

    # TODO: Expand outputs

    if args.output.endswith(".xlsx"):
        if "antibodies-submission" in args.output:
            antibodies.write_xlsx(args.output, grid["rows"])
        else:
            datasets.write_xlsx(
                args.output, find_assay_type_id(args.output), grid["rows"]
            )
    elif args.output.endswith(".html"):
        html = grids.grid_to_html(grid)
        templates.write_html("templates/grid.html", {"html": html}, args.output)
    else:
        raise Exception("Unsupported output format for '{0}'".format(args.output))


def main():
    main_parser = argparse.ArgumentParser()
    subparsers = main_parser.add_subparsers()

    parser = subparsers.add_parser("read", help="Read a table to STDOUT")
    parser.add_argument("input", help="The table file to read")
    parser.add_argument("sheet", help="The sheet to read", nargs="?", default=None)
    parser.set_defaults(func=read)

    parser = subparsers.add_parser(
        "expand", help="Expand a concise table to a labelled table"
    )
    parser.add_argument("input", help="The table file to read")
    parser.add_argument("sheet", help="The sheet to read", nargs="?", default=None)
    parser.add_argument("output", help="The file to write")
    parser.set_defaults(func=expand)

    parser = subparsers.add_parser(
        "fill", help="Use a TSV table to fill an Excel template"
    )
    parser.add_argument("input", help="The TSV file to read")
    parser.add_argument("output", help="The Excel file to write")
    parser.set_defaults(func=fill)

    parser = subparsers.add_parser("update", help="Update an Excel template")
    parser.add_argument("output", help="The Excel file to write")
    parser.set_defaults(func=update)

    parser = subparsers.add_parser("validate", help="Validate submission")
    parser.add_argument("input", help="The input file to validate")
    parser.add_argument("output", help="The output file to write")
    parser.set_defaults(func=validate)

    args = main_parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
