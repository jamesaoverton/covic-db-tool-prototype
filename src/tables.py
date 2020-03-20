#!/usr/bin/env python3

import csv


def read_tsv(path):
    with open(path, "r") as f:
        return list(csv.DictReader(f, delimiter="\t"))
