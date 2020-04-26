from collections import OrderedDict

from covicdbtools import names


def test_prefixes():
    prefixes = {"ex": "http://example.com/"}
    assert names.id_to_iri(prefixes, "ex:bar") == "http://example.com/bar"

    prefix, localname = names.split_id("ex:bar")
    assert prefix == "ex"
    assert localname == "bar"

    assert names.increment_id("ex:1") == "ex:2"


def test_concise_table():
    table = [OrderedDict({"foo": "bar"})]
    assert names.is_concise_table(table)

    table = [OrderedDict({"foo_id": "bar"})]
    assert names.is_concise_table(table)

    table = [OrderedDict({"foo_label": "bar"})]
    assert not names.is_concise_table(table)


def test_labelled_table():
    table = [OrderedDict({"foo": "bar"})]
    assert names.is_labelled_table(table)

    table = [OrderedDict({"foo_id": "bar"})]
    assert not names.is_labelled_table(table)

    table = [OrderedDict({"foo_id": "bar", "foo_label": "Bar"})]
    assert names.is_labelled_table(table)

    labels = {"bar": "Bar"}
    concise_table = [OrderedDict({"foo_id": "bar"})]
    labelled_table = [OrderedDict({"foo_id": "bar", "foo_label": "Bar"})]
    assert names.label_table(labels, concise_table) == labelled_table
    assert names.unlabel_table(labelled_table) == concise_table
