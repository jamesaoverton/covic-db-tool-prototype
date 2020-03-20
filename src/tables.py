#!/usr/bin/env python3

import csv


def read_tsv(path):
    with open(path, "r") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def write_tsv(odicts, path):
    with open(path, "w") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(odicts[0].keys())
        for row in odicts:
            w.writerow(row.values())
