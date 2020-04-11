### CoVIC-DB Tool Prototype Makefile
#
# James A. Overton <james@overton.ca>
#
# Usually you want to run:
#
#     make tidy all
#
# Requirements:
#
# - GNU Make
# - Python 3
# - Java
# - ROBOT <http://github.com/ontodev/robot>

### Configuration
#
# These are standard options to make Make sane:
# <http://clarkgrubb.com/makefile-style-guide#toc2>

MAKEFLAGS += --warn-undefined-variables
SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := all
.DELETE_ON_ERROR:
.SUFFIXES:
.SECONDARY:
.PHONY: all


### General Tasks

.PHONY: all
all: examples views

.PHONY: tidy
tidy:
	rm -rf build/datasets
	rm -f build/*.tsv build/*.owl $(VIEWS)

.PHONY: clobber
clobber: tidy
	rm -f build/CoVIC-DB.xlsx $(SHEET_TSVS)

.PHONY: clean
clean:
	rm -rf build

.PHONY: update
update:
	make clobber all

.PHONY: test
test:
	pytest tests

.PHONY: format
format:
	black src/covicdbtools/*.py tests/*.py
	shellcheck tests/*.sh


### Set Up

build build/datasets:
	mkdir -p $@


### ROBOT
#
# We use development versions of ROBOT for this project.

PREFIXES := --prefix "ONTIE: https://ontology.iedb.org/ontology/ONTIE_"
ROBOT := java -jar build/robot.jar $(PREFIXES)

build/robot.jar: | build
	curl -L -o $@ https://build.obolibrary.io/job/ontodev/job/robot/job/master/lastSuccessfulBuild/artifact/bin/robot.jar

build/robot-tree.jar: | build
	curl -L -o $@ https://build.obolibrary.io/job/ontodev/job/robot/job/tree-view/lastSuccessfulBuild/artifact/bin/robot.jar


### Tables
#
# These tables are stored in Google Sheets, and downloaded as TSV files.

ONTOLOGY_SHEETS = core hosts isotypes assays
SHEETS = prefixes $(ONTOLOGY_SHEETS) fields
SHEET_TSVS = $(foreach o,$(SHEETS),ontology/$(o).tsv)

build/CoVIC-DB.xlsx: | build
	curl -L -o $@ "https://docs.google.com/spreadsheets/d/11ItLLoXY7_r2lDazY4prMERHMb-7czrim91UABnvbYM/export?format=xlsx"

$(SHEET_TSVS): build/CoVIC-DB.xlsx
	xlsx2csv --delimiter tab --sheetname $(basename $(notdir $@)) $< > $@


### Ontology

build/imports.owl: $(foreach o,$(ONTOLOGY_SHEETS),ontology/$(o).tsv) | build/robot.jar
	$(ROBOT) template \
	$(foreach o,$(ONTOLOGY_SHEETS),--template ontology/$(o).tsv) \
	--output $@

build/ontology.owl: build/imports.owl ontology/protein-tree.owl | build/robot.jar
	$(ROBOT) merge \
	$(foreach o,$^,--input $(o)) \
	--output $@

build/labels.tsv: build/imports.owl | build/robot.jar
	$(ROBOT) export \
	--input $< \
	--header "ID|LABEL" \
	--export $@

config.json: src/covicdbtools/config.py $(SHEET_TSVS) build/labels.tsv
	python $^ $@

src/covicdbtools/cli.py: config.json

CVDB := python src/covicdbtools/cli.py


### Examples

ANTIBODIES_EXAMPLES = \
examples/antibodies-submission.xlsx \
examples/antibodies-submission-valid.xlsx \
build/antibodies-submission-valid-expanded.tsv \
build/antibodies-submission-valid-expanded.html \
examples/antibodies-submission-invalid.xlsx \
examples/antibodies-submission-invalid-highlighted.xlsx \
build/antibodies-submission-invalid-highlighted.html

DATASETS_EXAMPLES = \
examples/neutralization-submission.xlsx \
examples/neutralization-submission-valid.xlsx \
build/neutralization-submission-valid-expanded.tsv \
build/neutralization-submission-valid-expanded.html \
examples/neutralization-submission-invalid.xlsx \
examples/neutralization-submission-invalid-highlighted.xlsx \
build/neutralization-submission-invalid-highlighted.html \
examples/VLP-ELISA-submission.xlsx \
examples/VLP-ELISA-submission-valid.xlsx \
build/VLP-ELISA-submission-valid-expanded.tsv \
build/VLP-ELISA-submission-valid-expanded.html

examples/%-submission.xlsx: | src/covicdbtools/cli.py
	$(CVDB) fill $* "" $@

examples/%-submission-valid.xlsx: examples/%-submission-valid.tsv | src/covicdbtools/cli.py
	$(CVDB) fill $* $< $@

examples/%-submission-invalid.xlsx: examples/%-submission-invalid.tsv | src/covicdbtools/cli.py
	$(CVDB) fill $* $< $@

examples/%-submission-invalid-highlighted.xlsx: examples/%-submission-invalid.xlsx | src/covicdbtools/cli.py
	$(CVDB) validate $* $< $@

build/%-submission-invalid-highlighted.html: examples/%-submission-invalid.xlsx | src/covicdbtools/cli.py
	$(CVDB) validate $* $< $@

build/%-submission-valid-expanded.tsv: examples/%-submission-valid.xlsx | src/covicdbtools/cli.py
	$(CVDB) validate $* $< $@

build/%-submission-valid-expanded.html: examples/%-submission-valid.xlsx | src/covicdbtools/cli.py
	$(CVDB) validate $* $< $@

.PHONY: examples
examples: $(ANTIBODIES_EXAMPLES) $(DATASETS_EXAMPLES)



### Views

build/antibodies.html: src/covicdbtools/antibodies.py templates/grid.html ontology/prefixes.tsv ontology/fields.tsv build/labels.tsv build/antibodies.tsv | build
	python $^ $@

build/antibodies.tsv: build/antibodies-submission-valid-expanded.tsv
	cut -f1,4- $< | sed 's/VD-Crotty/COVIC/' > $@

build/datasets/%/dataset.html: src/covicdbtools/datasets.py templates/dataset.html ontology/prefixes.tsv build/labels.tsv data/datasets/%/ | build/datasets
	mkdir -p build/datasets/$*
	python $^ $@

build/summary.html: src/covicdbtools/summaries.py templates/grid.html ontology/prefixes.tsv ontology/fields.tsv build/labels.tsv build/antibodies.tsv build
	python $^ $@

build/index.html: src/covicdbtools/build-index.py templates/index.html | build
	python $^ $@

build/ontology.html: build/ontology.owl | build/robot-tree.jar
	java -jar build/robot-tree.jar $(PREFIXES) tree \
	--input $< \
	--tree $@

VIEWS := build/datasets/1/dataset.html build/summary.html build/index.html build/antibodies.html build/ontology.html

.PHONY: views
views: $(VIEWS)

