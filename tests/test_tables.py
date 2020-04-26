from collections import OrderedDict

from covicdbtools import tables


def test_is_table():
    table = "Foo"
    assert not tables.is_table(table)

    table = [{"foo": "bar"}]
    assert not tables.is_table(table)

    table = [OrderedDict({"foo": "bar"}), OrderedDict({"zoo": "baz"})]
    assert not tables.is_table(table)

    table = [OrderedDict({"foo": 1})]
    assert not tables.is_table(table)

    table = [OrderedDict({"foo": "bar"}), OrderedDict({"foo": "baz"})]
    assert tables.is_table(table)


def test_tsv_string():
    table = [
        OrderedDict({"foo": "bar", "a": "1"}),
        OrderedDict({"foo": "baz", "a": "2"}),
    ]
    string = """foo	a
bar	1
baz	2
"""
    assert tables.table_to_tsv_string(table) == string
