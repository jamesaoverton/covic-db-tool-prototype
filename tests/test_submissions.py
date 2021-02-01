from covicdbtools import submissions


def test_validate():
    headers = [{"value": "foo", "label": "Foo", "type": "integer"}]
    table = [{"Foo": 1}]
    result = submissions.validate(headers, table)
    assert "errors" not in result

    headers = [
        {"field": "ab_id", "label": "Antibody", "type": "id"},
        {"field": "ab_label", "label": "Antibody label", "type": "label"},
    ]
    table = [
        {"Antibody": "COVIC:1 Foo", "Antibody label": "COVIC-6 (batch1)"},
        {"Antibody": "  COVIC:1 Foo", "Antibody label": "  COVIC-6 (batch1)"},
    ]
    result = submissions.validate(headers, table)
    assert "errors" in result
    assert len(result["errors"]) == 4
