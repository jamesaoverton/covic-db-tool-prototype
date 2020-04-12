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
#  "path": "/absolute/path/to/result.xlsx",
#  "filename": "result.xlsx",
#  "content type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#  "content": "...",
# }
#
# The to_html() function will render the response into nice HTML.

from covicdbtools import grids


xlsx = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
tsv = "text/tab-separated-values"
html = "text/html"


def success(data={}):
    """Return a success response with given data."""
    if not isinstance(data, dict):
        data_type = type(data)
        raise Exception("Response data must be dict not '{data_type}'")
    data["status"] = 200
    data["message"] = "Success"
    return data


def failure(message, data={}):
    """Return a failure response with given message and data."""
    if not isinstance(data, dict):
        data_type = type(data)
        raise Exception("Response data must be dict not '{data_type}'")
    data["status"] = 400
    data["message"] = message
    return data


def validate(response):
    """Given a config dictionary, return None if it is valid,
    otherwise return a string describing the problem."""
    if not isinstance(response, dict):
        return "Response must be a dictionary"
    if not "status" in response:
        return "Response must have a status"
    status = response["status"]
    if status not in [200, 201, 400]:
        return "Unrecognized response status '{status}'"
    if not "message" in response:
        return "Response must have a message"
    if "content" in response and "content type" not in response:
        return "Response has 'content' but is missing 'content type'"
    if "content type" in response and "content" not in response:
        return "Response has 'content type' but is missing 'content'"
    return None


def is_response(response):
    result = validate(response)
    if result:
        return False
    return True


def succeeded(response):
    """Given a response, return True if it is a success, False otherwise."""
    if not is_response(response):
        return False
    return response["status"] == 200


def failed(response):
    return not succeeded(response)


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


def write(response):
    """Given a response with "path", "content type", and "path",
    write the content to the path."""
    if response["content type"].startswith("text"):
        with open(response["path"], "w") as w:
            w.write(response["content"])
    else:
        with open(response["path"], "wb") as w:
            w.write(response["content"].getvalue())
