from collections import OrderedDict

from covicdbtools import grids


def test_grid():
    grid = "Foo"
    assert not grids.is_grid(grid)

    grid = {}
    assert not grids.is_grid(grid)

    grid = {"rows": {}}
    assert not grids.is_grid(grid)

    grid = {"rows": []}
    assert not grids.is_grid(grid)

    grid = {"rows": ["Foo"]}
    assert not grids.is_grid(grid)

    grid = {"rows": [{"value": "foo"}]}
    assert not grids.is_grid(grid)

    grid = {"headers": "Foo", "rows": ["Foo"]}
    assert not grids.is_grid(grid)

    prefixes = {"ex": "http://example.com/"}
    fields = {"foo_id": {"label": "Foo"}}
    labelled_table = [OrderedDict({"foo_id": "ex:bar", "foo_label": "Bar"})]
    grid = {
        "headers": [[{"label": "Foo", "value": "foo_id"}]],
        "rows": [[{"iri": "http://example.com/bar", "label": "Bar", "value": "ex:bar"}]],
    }
    assert grids.table_to_grid(prefixes, fields, labelled_table) == grid


def test_grid_to_html():
    grid = {
        "headers": [[{"label": "Foo", "value": "foo_id"}]],
        "rows": [[{"iri": "http://example.com/bar", "label": "Bar", "value": "ex:bar"}]],
    }
    html = """<table class="table">
  <thead>
    <tr>
      <th>Foo</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><a href="http://example.com/bar">Bar</a></td>
    </tr>
  </tbody>
</table>"""
    assert grids.grid_to_html(grid) == html
