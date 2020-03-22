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

VIEWS := build/datasets/1/dataset.html build/summary.html build/index.html build/antibodies.html build/ontology.html

.PHONY: all
all: $(VIEWS)

.PHONY: tidy
tidy:
	rm -rf build/datasets
	rm -f build/*.tsv $(VIEWS)

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
	pytest

.PHONY: format
format:
	black src/covicdbtools/*.py tests/*.py


### Set Up

build build/datasets:
	mkdir -p $@


### ROBOT
#
# We use development versions of ROBOT for this project.

ROBOT := java -jar build/robot.jar

build/robot.jar: | build
	curl -L -o $@ https://build.obolibrary.io/job/ontodev/job/robot/job/master/lastSuccessfulBuild/artifact/bin/robot.jar

build/robot-tree.jar: | build
	curl -L -o $@ https://build.obolibrary.io/job/ontodev/job/robot/job/tree-view/lastSuccessfulBuild/artifact/bin/robot.jar

### Tables
#
# These tables are stored in Google Sheets, and downloaded as TSV files.

SHEETS = prefixes imports fields
SHEET_TSVS = $(foreach o,$(SHEETS),ontology/$(o).tsv)

build/CoVIC-DB.xlsx: | build
	curl -L -o $@ "https://docs.google.com/spreadsheets/d/11ItLLoXY7_r2lDazY4prMERHMb-7czrim91UABnvbYM/export?format=xlsx"

$(SHEET_TSVS): build/CoVIC-DB.xlsx
	xlsx2csv --delimiter tab --sheetname $(basename $(notdir $@)) $< > $@

build/labels.tsv: ontology/imports.tsv | build
	sed '2d' $< \
	| cut -f1-2 \
	> $@


### Ontology

build/ontology/imports.owl: ontology/imports.tsv | build/robot.jar
	$(ROBOT) template --template $< --output $@

build/ontology.owl: build/ontology/imports.owl ontology/protein-tree.owl | build/robot.jar
	$(ROBOT) merge \
	$(foreach o, $^, --input $(o)) \
	--output $@


### Views

build/antibodies.html: src/antibodies.py templates/grid.html ontology/prefixes.tsv ontology/fields.tsv build/labels.tsv data/antibodies.tsv | build
	python $^ $@

build/datasets/%/dataset.html: src/datasets.py templates/dataset.html ontology/prefixes.tsv build/labels.tsv data/datasets/%/ | build/datasets
	mkdir -p build/datasets/$*
	python $^ $@

build/summary.html: src/summaries.py templates/grid.html ontology/prefixes.tsv ontology/fields.tsv build/labels.tsv data/antibodies.tsv data/datasets/ | build
	python $^ $@

build/index.html: src/build-index.py templates/index.html | build
	python $^ $@

build/ontology.html: build/ontology.owl | build/robot-tree.jar
	java -jar build/robot-tree.jar tree \
	--input $< \
	--tree $@
