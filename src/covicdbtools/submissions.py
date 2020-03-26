from collections import defaultdict, OrderedDict
from covicdbtools import grids


def store(headers, table):
    """Given the headers and a (validated!) table,
    return a table of the submission."""
    submission = []
    for row in table:
        newrow = OrderedDict()
        for header in headers:
            value = header["value"]
            label = header["label"]
            newrow[value] = row[label]
        submission.append(newrow)

    # TODO: actually store the data!
    return submission


def validate(headers, table):
    """Given the headers and a (validated!) table, return None if it is valid,
    otherwise return a grid with problems marked
    and an "errors" key with a list of errors."""
    errors = []
    rows = []
    unique = defaultdict(set)

    for i in range(0, len(table)):
        row = table[i]
        first_value = row[0]["value"].strip() if "value" in row else None
        newrow = []

        for header in headers:
            column = header["label"]
            value = row[column].strip() if column in row else ""
            error = None
            if "required" in header and header["required"] and first_value and value == "":
                error = "Missing required value for '{0}'".format(column)
            elif "unique" in header and header["unique"] and value in unique[column]:
                error = "Duplicate value '{0}' is not allowed for '{1}'".format(
                    value, column
                )
            elif (
                "terminology" in header
                and value != ""
                and value not in header["terminology"]
            ):
                error = "'{0}' is not a recognized value for '{1}'".format(
                    value, column
                )
            if "type" in header and value != "":
                if header["type"] == "float":
                    try:
                        _ = float(value)
                    except:
                        error = "'{0}' is not of type '{1}'".format(
                            value, header["type"]
                        )
                # TODO: Handle bad types
            if "unique" in header and header["unique"]:
                unique[column].add(value)

            cell = None
            if error:
                cell = grids.error_cell(value, error)
                errors.append("Error in row {0}: {1}".format(i + 1, error))
            else:
                cell = grids.value_cell(value)
            newrow.append(cell)

        rows.append(newrow)

    if len(errors) > 0:
        return {"errors": errors, "headers": [headers], "rows": rows}
    return None
