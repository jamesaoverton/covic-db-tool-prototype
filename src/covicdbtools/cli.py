#!/usr/bin/env python

import argparse
import os

from covicdbtools import (
    config,
    names,
    tables,
    grids,
    workbooks,
    templates,
    antibodies,
    datasets,
    submissions,
)


def find_assay_type_id(assay_name):
    assay_name = assay_name.replace("-", " ")
    if assay_name in config.assays:
        return config.assays[assay_name]["id"]
    raise Exception(f"Unrecognized assay name '{assay_name}'")


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

    table = names.label_table(config.labels, table)

    if args.output.endswith(".tsv"):
        tables.write_tsv(table, args.output)
    elif args.output.endswith(".html"):
        grid = grids.table_to_grid(config.prefixes, config.fields, table)
        html = grids.grid_to_html(grid)
        templates.write_html("templates/grid.html", {"html": html}, args.output)
    else:
        raise Exception("Unsupported output format for '{0}'".format(args.output))


def fill(args):
    rows = []
    if args.input != "":
        table = tables.read_tsv(args.input)
        grid = grids.table_to_grid(config.prefixes, config.fields, table)
        rows = grid["rows"]
    if args.type == "antibodies":
        antibodies.write_xlsx(args.output, rows)
    else:
        datasets.write_xlsx(args.output, find_assay_type_id(args.type), rows)


def validate(args):
    table = None
    grid = None
    assay_id = None
    if args.type != "antibodies":
        assay_id = find_assay_type_id(args.type)

    if args.input.endswith(".xlsx"):
        if args.type == "antibodies":
            table = workbooks.read_xlsx(args.input, "Antibodies")
            grid = antibodies.validate_submission(table)
        else:
            table = workbooks.read_xlsx(args.input, "Dataset")
            grid = datasets.validate_submission(assay_id, table)
    elif args.input.endswith(".tsv"):
        table = tables.read_tsv(args.input)
        if args.type == "antibodies":
            grid = antibodies.validate_submission(table)
        else:
            grid = datasets.validate_submission(assay_id, table)
    else:
        raise Exception(f"Unsupported input format for '{args.input}'")

    # TODO: Expand outputs
    if not grid:
        if args.type == "antibodies":
            table = antibodies.store_submission("org:1", "LJI", table)
        else:
            table = datasets.store_submission(assay_id, table)
        grid = grids.table_to_grid(config.prefixes, config.fields, table)

    if args.output.endswith(".xlsx"):
        if args.type == "antibodies":
            antibodies.write_xlsx(args.output, grid["rows"])
        else:
            datasets.write_xlsx(args.output, assay_id, grid["rows"])
    elif args.output.endswith(".html"):
        html = grids.grid_to_html(grid)
        templates.write_html("templates/grid.html", {"html": html}, args.output)
    elif "errors" in grid:
        for error in errors:
            print(error)
        raise Exception(
            "Validation errors cannot be stored in chosen format '{0}'".format(
                args.output
            )
        )
    elif args.output.endswith(".tsv"):
        tables.write_tsv(table, args.output)
    else:
        raise Exception("Unsupported output format for '{0}'".format(args.output))


def main():
    config.update_config()

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
    parser.add_argument("type", help="The type of template to fill")
    parser.add_argument("input", help="The TSV file to read")
    parser.add_argument("output", help="The Excel file to write")
    parser.set_defaults(func=fill)

    parser = subparsers.add_parser("validate", help="Validate submission")
    parser.add_argument("type", help="The type of template to validate")
    parser.add_argument("input", help="The input file to validate")
    parser.add_argument("output", help="The output file to write")
    parser.set_defaults(func=validate)

    args = main_parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
