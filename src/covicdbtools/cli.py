#!/usr/bin/env python

import argparse
import sys

from covicdbtools import api, config, responses, tables


def guard(response):
    """Given a successful response, just return it,
    otherwise print an error message and exit."""
    if not responses.is_response(response):
        raise Exception(f"Bad response: {response}")
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


def initialize(args):
    """Create the global data repositories."""
    api.initialize()


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


def fetch_template(args):
    """Fetch the empty template for a given data type, then write it."""
    response = guard(api.fetch_template(args.type))
    response["path"] = args.output
    responses.write(response)


def maybe_write(response, datatype, output):
    if output and output.endswith(".xlsx"):
        response = guard(api.fill_rows(datatype, response["grid"]["rows"]))
        response["path"] = output
        responses.write(response)
    elif output:
        response = guard(api.convert(response["grid"], output))
        response["path"] = output
        responses.write(response)
    return response


def validate(args):
    """Validate a table and optionally write the result."""
    response = api.validate(args.type, args.input)
    guard(maybe_write(response, args.type, args.output))


def submit_antibodies(args):
    """Submit a table, validate, store, and optionally write the result."""
    response = api.submit_antibodies(
        args.name, args.email, args.organization, args.input
    )
    guard(maybe_write(response, "antibodies", args.output))


def submit_assays(args):
    """Submit a table, validate, store, and optionally write the result."""
    response = api.submit_assays(args.name, args.email, args.id, args.input)
    guard(maybe_write(response, args.id, args.output))


def create_dataset(args):
    """Create a new dataset with a given assay type."""
    guard(api.create_dataset(args.name, args.email, args.type))


def promote_dataset(args):
    """Promote a new dataset from staging to public."""
    guard(api.promote_dataset(args.name, args.email, args.id))


def main():
    main_parser = argparse.ArgumentParser()
    subparsers = main_parser.add_subparsers(required=True, dest="cmd")

    parser = subparsers.add_parser(
        "initialize", help="Initialize the data repositories"
    )
    parser.set_defaults(func=initialize)

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

    parser = subparsers.add_parser("fetch", help="Fetch an Excel file")
    subsubparsers = parser.add_subparsers(required=True, dest="cmd")
    parser = subsubparsers.add_parser("template", help="Fetch an empty Excel template")
    parser.add_argument("type", help="The type of template to fetch")
    parser.add_argument("output", help="The output file to write")
    parser.set_defaults(func=fetch_template)

    parser = subparsers.add_parser("validate", help="Validate data")
    parser.add_argument("type", help="The type of data to validate")
    parser.add_argument("input", help="The input file to validate")
    parser.add_argument("output", help="The output file to write", nargs="?")
    parser.set_defaults(func=validate)

    parser = subparsers.add_parser("submit", help="Submit data")
    subsubparsers = parser.add_subparsers(required=True, dest="cmd")
    parser = subsubparsers.add_parser("antibodies", help="Submit antibodies")
    parser.add_argument("name", help="The submitter's name")
    parser.add_argument("email", help="The submitter's email")
    parser.add_argument("organization", help="The submitter's organization")
    parser.add_argument("input", help="The input file to submit")
    parser.add_argument("output", help="The output file to write", nargs="?")
    parser.set_defaults(func=submit_antibodies)
    parser = subsubparsers.add_parser("assays", help="Submit assays")
    parser.add_argument("name", help="The submitter's name")
    parser.add_argument("email", help="The submitter's email")
    parser.add_argument("id", help="The dataset id")
    parser.add_argument("input", help="The input file to submit")
    parser.add_argument("output", help="The output file to write", nargs="?")
    parser.set_defaults(func=submit_assays)

    parser = subparsers.add_parser("create", help="Create a new entry")
    subsubparsers = parser.add_subparsers(required=True, dest="cmd")
    parser = subsubparsers.add_parser("dataset", help="Create a new dataset")
    parser.add_argument("name", help="The submitter's name")
    parser.add_argument("email", help="The submitter's email")
    parser.add_argument("type", help="The type of data to submit")
    parser.set_defaults(func=create_dataset)

    parser = subparsers.add_parser(
        "promote", help="Promote data from staging to public"
    )
    subsubparsers = parser.add_subparsers(required=True, dest="cmd")
    parser = subsubparsers.add_parser(
        "dataset", help="Promote a dataset from staging to public"
    )
    parser.add_argument("name", help="The submitter's name")
    parser.add_argument("email", help="The submitter's email")
    parser.add_argument("id", help="The dataset ID to promote")
    parser.set_defaults(func=promote_dataset)

    args = main_parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
