import re

from collections import defaultdict, OrderedDict
from covicdbtools import config, names, grids
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


def validate_mutation(value):
    match = re.match(r"^(\w)(\d+)(\w)$", value)
    if match:
        # print("point mutation", value)
        if match[1] not in "ACDEFGHIKLMNPQRSTVWXY":
            return f"'{value}' is not a valid mutation: old amino acid is not valid"
        if match[3] not in "ACDEFGHIKLMNPQRSTVWXY":
            return f"'{value}' is not a valid mutation: old amino acid is not valid"
        if match[1] == match[3]:
            return f"'{value}' is not a valid mutation: old and new amino acids are the same"
        return None

    match = re.match(r"^del\d+$", value)
    if match:
        # print("point deletion", value)
        return None

    match = re.match(r"^del(\d+)-(\d+)$", value)
    if match:
        # print("range deletion", value)
        start = int(match[1])
        end = int(match[2])
        if start >= end:
            return f"'{value}' is not a valid mutation: start position must be before end position"
        return None

    return f"'{value}' is not a valid mutation"


def validate_field(column, field_type, value):
    if field_type == "text":
        return None

    elif field_type == "label":
        return None

    elif field_type == "id":
        if names.is_id(config.prefixes, value):
            return None
        return f"'{value}' is not a valid ID in column '{column}'"

    elif field_type == "integer":
        try:
            _ = int(value)
            return None
        except ValueError:
            return f"'{value}' is not of type '{field_type}' in column '{column}'"

    elif field_type == "non-negative integer":
        try:
            i = int(value)
            if i < 0:
                return f"'{value}' must be a non-negative integer in column '{column}'"
            return None
        except ValueError:
            return f"'{value}' is not of type '{field_type}' in column '{column}'"

    elif field_type == "score_0_5":
        try:
            x = int(value)
            if x < 0 or x > 5:
                return f"'{value}' is not in range 0-5 in '{column}'"
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
            _ = float(value.lstrip("<>"))
            return None
        except ValueError:
            return f"'{value}' is not of type '{field_type}' in column '{column}'"

    elif field_type == "percent":
        try:
            _ = float(value)
            return None
        except ValueError:
            return f"'{value}' is not of type '{field_type}' in column '{column}'"

    elif field_type == "mutations":
        try:
            mutations = value.split(",")
            error = None
            for mutation in mutations:
                error = validate_mutation(mutation)
                if error:
                    return error
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
    blinded_antibodies = config.read_blinded_antibodies()
    ab_ids = [x["ab_id"] for x in blinded_antibodies] + [
        x["id"] for x in config.ab_controls.values()
    ]
    ab_labels = [x["ab_id"].replace(":", "-") for x in blinded_antibodies] + list(
        config.ab_controls.keys()
    )

    columns = set()
    for header in headers:
        try:
            columns.add(header["label"])
        except KeyError as e:
            raise Exception(f"Bad header {header}", e)

    new_table = []
    for i in range(0, len(table)):
        row = table[i]

        # Skip blank rows
        values = ""
        for value in row.values():
            values += str(value).strip()
        if values == "":
            continue
        new_table.append(row)

        extra_columns = set(row.keys()) - columns
        extra_columns.discard(None)
        if extra_columns:
            extra = ", ".join(extra_columns)
            errors.append(f"Extra columns not allowed: {extra}")

        missing_columns = columns - set(row.keys())
        if missing_columns:
            missing = ", ".join(missing_columns)
            errors.append(f"Missing columns: {missing}")

        newrow = []
        for header in headers:
            column = header["label"]
            error = None
            if column not in row:
                # Should be handled above
                continue
            value = str(row[column]).strip()
            if "field" in header and header["field"] == "ab_id":
                if value not in ab_ids:
                    error = (
                        f"'{value}' is not a valid COVIC antibody ID or control antibody ID "
                        + "in column 'Antibody ID'"
                    )
            elif "field" in header and header["field"] == "ab_label":
                if value not in ab_labels:
                    error = (
                        f"'{value}' is not a valid COVIC antibody label or control antibody label "
                        + "in column 'Antibody label'"
                    )
            elif "required" in header and header["required"] and value == "":
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
                errors.append("Error in row {0}: {1}".format(i + 2, error))
            else:
                cell = grids.value_cell(value)
            newrow.append(cell)

        rows.append(newrow)

    table = new_table
    grid = {"headers": [headers], "rows": rows}
    unique_errors = []
    for error in errors:
        if error not in unique_errors:
            unique_errors.append(error)
    errors = unique_errors
    error_count = len(errors)
    if error_count > 0:
        return failure(
            f"There were {error_count} errors",
            {"errors": errors, "table": table, "grid": grid},
        )
    return success({"table": table, "grid": grid})
