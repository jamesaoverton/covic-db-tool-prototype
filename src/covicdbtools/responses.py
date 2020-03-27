### Responses Utilities
#
# A "response" is a dictionary that with an HTTP status and some other optional values:
#
# {"status": 400,
#  "message": "There some sort of error",
#  "errors": ["List of errors"],
#  "exception": FooException,
#  "grid": {"headers": [[...]], "rows": [[...]]},
#  "table": [OrderedDict(...)],
#  "path": "/absolute/path/to/result.xlsx"
# }
#
# The to_html() function will render the response into nice HTML.

from covicdbtools import grids


def to_html(response, prefixes={}, fields={}):
    lines = ["<div>"]
    if "message" in response:
        lines.append("  <p>{0}</p>".format(response["message"]))
    if "exception" in response:
        lines.append("  <p>{0}</p>".format(str(response["exception"])))
    if "errors" in response:
        lines.append("  <p>Errors</p>")
        lines.append("  <ul>")
        for error in response["errors"]:
            lines.append("    <li>{0}</li>".format(error))
        lines.append("  </ul>")
    if "grid" in response:
        lines.append(grids.grid_to_html(response["grid"]))
    elif "table" in response:
        lines.append(
            grids.grid_to_html(grids.table_to_grid(prefixes, fields, response["table"]))
        )
    lines.append("</div>")
    return "\n".join(lines)
