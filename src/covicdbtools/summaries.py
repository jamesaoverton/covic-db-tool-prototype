#!/usr/bin/env python3

import argparse
import os

from covicdbtools import config, tables, grids, templates


def read_data(
    antibodies_tsv_path,
    dataset_path,
):
    # ab_list = antibodies.read_antibodies(config.labels, antibodies_tsv_path)
    ab_table = tables.read_tsv(antibodies_tsv_path)
    grid = grids.table_to_grid(config.prefixes, config.fields, ab_table)
    cell = grids.value_cell("")
    cell["colspan"] = len(grid["headers"][0])
    grid["headers"].insert(0, [cell])

    for root, dirs, files in os.walk(dataset_path):
        for name in files:
            if name.startswith("antibodies"):
                continue
            if name.endswith("-valid-expanded.tsv"):
                assays_tsv_path = os.path.join(root, name)
                assay_name = name.replace("-submission-valid-expanded.tsv", "").replace("-", " ")
                assay_table = tables.read_tsv(assays_tsv_path)
                columns = len(assay_table[0].keys()) - 1
                assay_grid = grids.table_to_grid(config.prefixes, config.fields, assay_table)

                ab_map = {}
                for row in assay_grid["rows"]:
                    ab_label = row[0]["value"]
                    row.pop(0)
                    ab_map[ab_label] = row

                header = grids.value_cell(assay_name)
                header["colspan"] = columns
                grid["headers"][0].append(header)
                grid["headers"][1] += assay_grid["headers"][0][1:]

                for row in grid["rows"]:
                    ab_label = row[0]["value"].replace(":", " ")
                    if ab_label in ab_map:
                        row += ab_map[ab_label]
                    else:
                        for column in range(0, columns):
                            row.append(grids.value_cell(""))

    grid["message"] = "This is the public view with all antibodies (blinded) and assays."
    return grid


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert dataset text files to HTML")
    parser.add_argument("template", type=str, help="The template to use")
    parser.add_argument("antibodies", type=str, help="The antibodies table")
    parser.add_argument("datasets", type=str, help="The datasets directory")
    parser.add_argument("output", type=str, help="The output file")
    args = parser.parse_args()

    grid = read_data(args.antibodies, args.datasets)
    templates.write_html(
        args.template,
        {"message": grid["message"], "html": grids.grid_to_html(grid)},
        args.output,
    )
