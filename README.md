# CoVIC-DB Tool Prototype

This is a preliminary prototype for working with [IEDB](http://iedb.org)-style data in a git repository. Requirements are GNU Make, Python 3 (see `requirements.txt`), and Java 8.

The data is in a separate repository: https://github.com/jamesaoverton/covic-db-data-prototype

A demo is here: https://cvdb.ontodev.com

Supporting Google Sheet is here: https://docs.google.com/spreadsheets/d/11ItLLoXY7_r2lDazY4prMERHMb-7czrim91UABnvbYM


## Usage

This repository serves two purposes:

1. build an ontology to support the CoVIC-DB project
2. provide a library and command-line tool for working with CoVIC-DB data


### Ontology

Building the ontology requires GNU Make, Java 8+, and xlx2csv. Run `make ontology`.

We use this ontology to build the `src/covicdbtools/config.json` file used by the library and command-line tool, and after that point Java is not required.


### Library

The library is a Python 3 module. We suggest using `virtualenv` and installing with `pip install -e .`. Please set the `CVDB_DATA` environment variable to the directory where your git data repositories will be stored, e.g. `data/`. Common functionality is exposed through `covicdbtools.api`:

1. `api.initialize()` create the required git data repositories in `$CVDB_DATA`
2. `api.fetch_template("antibodies")` fetch the empty antibodies Excel template
3. `api.submit_antibodies(name, email, organization, request)` submit an Excel template filled with antibody entries
4. `api.create_dataset(name, email, assay_type)` create a new dataset for the given assay type
5. `api.fetch_template(dataset_id)` fetch the empty Excel template for this dataset
6. `api.submit_assays(name, email, dataset_id, request)` submit an Excel template filled with assay entries
7. `api.promote_dataset(name, email, dataset_id)` promote a dataset from staging to public

All these functions return `response` dictionaries, which include a `"status"` indicating success or failure and a `"message"`. Failed responses may include `"errors"`. The `fetch_template` and `submit_*` responses will usually include `"content"` with `BytesIO` for an Excel file.


### Command Line

The API functionality is also accessible through a command-line client at `src/covicdbtools/cli.py`, which `pip` should alias to `cvdb`. See `cvdb --help` for more information.


## Design

One of our goals is to create [Linked Data](http://linkeddata.org). At the most basic level, this means:

1. all of our public identifiers can be expanded to public URLs
2. we distinguish individual things from classes of things, and use ontologies to identify the classes

[IRI](https://tools.ietf.org/html/rfc3987)s are a superset of [URL](https://url.spec.whatwg.org)s that allow for URNs and for Unicode characters. We'll use "IRI" throughout, but all of our IRIs are in the HTTP(S) URL subset.

IRIs are globally unique, but can be inconveniently long, so we use the [CURIE](https://www.w3.org/TR/curie/) standard for our IDs. For example, if we want to talk about the class of all mice, we can use the term 'Mus musculus' from the [NCBI Taxonomy](https://www.ncbi.nlm.nih.gov/taxonomy). The IRI <http://purl.obolibrary.org/obo/NCBITaxon_10090> has been assign to 'Mus musculus'. We can define a prefix 'NCBITaxon' with base 'http://purl.obolibrary.org/obo/NCBITaxon_' for use throughout our system. Then we can refer to 'Mus musculus' by the ID 'NCBITaxon:10090', which is short and convenient, and expands to a globally unique IRI.

We define a list of all our prefixes in `ontology/prefixes.tsv`. We use IDs wherever possible. If a column of a table contains an ID, we adopt the convention of appending '_id'. If a column contains the ID for a class, we append '_type_id'.

| ab_id | host_type_id    | isotype |
|-------|-----------------|---------|
| ab:1  | NCBITaxon:10090 | foo     |

Our convention is to store tables as TSV on the filesystem. In Python, we use the `csv.DictReader` and represent tables as lists of `OrderedDict`s.

We usually want to associate a human-readable label with each ID. We define functions for adding '_label' columns, with results like this:

| ab_id | ab_label | host_type_id    | host_type_label    | isotype |
|-------|----------|-----------------|--------------------|---------|
| ab:1  | mAb 1    | NCBITaxon:10090 | Mus musculus       | foo     |

We also define functions for removing the '_label' columns. If a table does not include labels, we call it a "concise table". If a table does include labels, we call it a "labelled template".

To help display tables as pretty HTML and Excel, we define a "grid", consisting of header rows and data rows. Each cell is represented by a Python dictionary, containing a "value" key, which may also include "iri", "label", "status", "comment", and other keys. We provide functions for converting labelled tables to grids, and grids to HTML and Excel. Our example table can be converted to this HTML:

<table class="table">
  <thead>
    <tr>
      <th>Antibody</th>
      <th>Host</th>
      <th>Isotype</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><a href="#ab_1">mAb 1</a></td>
      <td><a href="http://purl.obolibrary.org/obo/NCBITaxon_10090">Mus musculus</a></td>
      <td>foo</td>
    </tr>
  </tbody>
</table>
