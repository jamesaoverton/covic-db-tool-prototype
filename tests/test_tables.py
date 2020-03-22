from collections import OrderedDict

from covicdbtools import tables


def test_is_table():
    table = "Foo"
    assert tables.is_table(table) == False

    table = []
    assert tables.is_table(table) == False

    table = [{"foo": "bar"}]
    assert tables.is_table(table) == False

    table = [OrderedDict({"foo": "bar"}), OrderedDict({"zoo": "baz"})]
    assert tables.is_table(table) == False

    table = [OrderedDict({"foo": 1})]
    assert tables.is_table(table) == False

    table = [OrderedDict({"foo": "bar"}), OrderedDict({"foo": "baz"})]
    assert tables.is_table(table) == True


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
