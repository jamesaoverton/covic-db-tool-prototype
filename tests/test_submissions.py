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
        {"Antibody": "ONTIE:0003596", "Antibody label": "isotype control"},
    ]
    result = submissions.validate(headers, table)
    assert "errors" in result
    assert len(result["errors"]) == 4


def test_validate_field():
    assert submissions.validate_field("foo", "score 0-1", "0.00000") is None
    assert submissions.validate_field("foo", "score 0-1", "1.00000") is None
    assert submissions.validate_field("foo", "score 0-1", "0") is None

    mutations = "L18F, D80A, D215G, del241-243, R246I, K417N, E484K, N501Y, D614G, A701V"
    assert submissions.validate_field("foo", "mutations", mutations) is None

    assert submissions.validate_field("foo", "score 0-1", "X") is not None
    assert submissions.validate_field("foo", "score 0-1", "1.00001") is not None
    assert submissions.validate_field("foo", "score 0-1", "-1.00001") is not None


def test_validate_mutation():
    assert submissions.validate_mutation("A1C") is None
    assert submissions.validate_mutation("del2") is None
    assert submissions.validate_mutation("del3-4") is None

    assert submissions.validate_mutation("A1B") is not None
    assert submissions.validate_mutation("A1A") is not None
    assert submissions.validate_mutation("del") is not None
    assert submissions.validate_mutation("del2-1") is not None
