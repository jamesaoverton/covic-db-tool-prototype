from covicdbtools import submissions


def test_validate():
    headers = [{"value": "foo", "label": "Foo", "type": "integer"}]
    table = [{"foo": 1}]
    assert submissions.validate(headers, table)
