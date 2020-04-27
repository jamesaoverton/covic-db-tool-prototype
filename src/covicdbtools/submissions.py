from collections import defaultdict, OrderedDict
from covicdbtools import names, grids
from covicdbtools.responses import success, failure


def store(ids, headers, table):
    """Given the IDs map, headers list, and a (validated!) table,
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


def validate_field(column, field_type, value):
    if field_type == "text":
        return None

    elif field_type == "label":
        return None

    elif field_type == "id":
        if names.is_id(value):
            return None
        return f"'{value}' is not a valid ID in column '{column}'"

    elif field_type == "int":
        try:
            _ = int(value)
            return None
        except ValueError:
            return f"'{value}' is not of type '{field_type}' in column '{column}'"

    elif field_type == "float":
        try:
            _ = float(value)
            return None
        except ValueError:
            return f"'{value}' is not of type '{field_type}' in column '{column}'"

    elif field_type == "float_na":
        if value == "" or value.lower() == "na":
            return None
        try:
            _ = float(value)
            return None
        except ValueError:
            return f"'{value}' is not of type '{field_type}' in column '{column}'"

    elif field_type == "float_threshold_na":
        if value == "" or value.lower() == "na":
            return None
        try:
            _ = float(value.lstrip("<"))
            return None
        except ValueError:
            return f"'{value}' is not of type '{field_type}' in column '{column}'"

    return f"Unrecognized field type '{field_type}' in column '{column}'"


def validate(headers, table):
    """Given the headers and a (validated!) table,
    return a response with "grid" and maybe "errors"."""
    errors = []
    rows = []
    unique = defaultdict(set)

    for i in range(0, len(table)):
        row = table[i]
        values = ""
        for value in row.values():
            values += value.strip()
        if values == "":
            continue

        newrow = []
        for header in headers:
            column = header["label"]
            value = row[column].strip() if column in row else ""
            error = None
            if "required" in header and header["required"] and value == "":
                error = f"Missing required value in column '{column}'"
            elif "unique" in header and header["unique"] and value in unique[column]:
                error = f"Duplicate value '{value}' is not allowed in column '{column}'"
            elif "terminology" in header and value != "" and value not in header["terminology"]:
                error = f"'{value}' is not a valid term in column '{column}'"
            elif "type" in header and value != "":
                error = validate_field(column, header["type"], value)
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

    grid = {"headers": [headers], "rows": rows}
    error_count = len(errors)
    if error_count > 0:
        return failure(
            f"There were {error_count} errors", {"errors": errors, "table": table, "grid": grid},
        )
    return success({"table": table, "grid": grid})
