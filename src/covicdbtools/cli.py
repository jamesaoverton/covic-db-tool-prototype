#!/usr/bin/env python

import argparse
import sys

from covicdbtools import api, config, responses, tables


def guard(response):
    """Given a successful response, just return it,
    otherwise print an error message and exit."""
    if not response:
        print("Bad response:", response)
        sys.exit(1)
    if response and responses.succeeded(response):
        return response
    if "message" in response:
        print(response["message"])
    if "errors" in response:
        for error in response["errors"]:
            print(error)
    if "exception" in response:
        print(response["exception"])
    sys.exit(1)


def read(args):
    """Read a table and print to STDOUT."""
    response = guard(api.read(args.input, args.sheet))
    tables.print_tsv(response["table"])


def expand(args):
    """Read a table, expand IDs and labels, then write it."""
    response = guard(api.expand(args.input, args.sheet))
    response = guard(api.convert(response["table"], args.output))
    response["path"] = args.output
    responses.write(response)


def convert(args):
    """Read a table and save it to another format."""
    response = guard(api.read(args.input, args.sheet))
    response = guard(api.convert(response["table"], args.output))
    response["path"] = args.output
    responses.write(response)


def fill(args):
    """Fill a template with optional table of data then write it."""
    response = guard(api.fill(args.type, args.input))
    response["path"] = args.output
    responses.write(response)


def maybe_write(response, datatype, output):
    if output and output.endswith(".xlsx"):
        response = guard(api.fill_rows(datatype, response["grid"]["rows"]))
    elif output:
        response = guard(api.convert(response["grid"], output))
        response["path"] = output
        responses.write(response)
    return response


def validate(args):
    """Validate a table and optionally write the result."""
    response = api.validate(args.type, args.input)
    guard(maybe_write(response, args.type, args.output))


def submit(args):
    """Submit a table, validate, store, and optionally write the result."""
    response = api.submit(args.name, args.email, args.type, args.input)
    guard(maybe_write(response, args.type, args.output))


def create(args):
    """Create a new dataset with a given assay type."""
    guard(api.create(args.name, args.email, args.type))


def main():
    config.update()

    main_parser = argparse.ArgumentParser()
    subparsers = main_parser.add_subparsers()

    parser = subparsers.add_parser("read", help="Read a table to STDOUT")
    parser.add_argument("input", help="The table file to read")
    parser.add_argument("sheet", help="The sheet to read", nargs="?", default=None)
    parser.set_defaults(func=read)

    parser = subparsers.add_parser("convert", help="Convert a table to another format")
    parser.add_argument("input", help="The table file to read")
    parser.add_argument("sheet", help="The sheet to read", nargs="?", default=None)
    parser.add_argument("output", help="The file to write")
    parser.set_defaults(func=convert)

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

    parser = subparsers.add_parser("validate", help="Validate data")
    parser.add_argument("type", help="The type of data to validate")
    parser.add_argument("input", help="The input file to validate")
    parser.add_argument("output", help="The output file to write", nargs="?")
    parser.set_defaults(func=validate)

    parser = subparsers.add_parser("submit", help="Submit data")
    parser.add_argument("name", help="The submitter's name")
    parser.add_argument("email", help="The submitter's email")
    parser.add_argument("type", help="The type of data to submit")
    parser.add_argument("input", help="The input file to submit")
    parser.add_argument("output", help="The output file to write", nargs="?")
    parser.set_defaults(func=submit)

    parser = subparsers.add_parser("create", help="Create a new dataset")
    parser.add_argument("name", help="The submitter's name")
    parser.add_argument("email", help="The submitter's email")
    parser.add_argument("type", help="The type of data to submit")
    parser.set_defaults(func=create)

    args = main_parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
