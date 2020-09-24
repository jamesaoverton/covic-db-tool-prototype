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
all: config examples views

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
	touch examples/*.tsv
	make clobber all

PYTHON_FILES := src/covicdbtools tests

.PHONY: test
test:
	pytest tests
	rm -rf temp
	tests/script.sh

.PHONY: lint
lint:
	flake8 --max-line-length 100 --ignore E203,W503 $(PYTHON_FILES)
	black --quiet --line-length 100 --check $(PYTHON_FILES)
	shellcheck tests/*.sh

.PHONY: format
format:
	black --quiet --line-length 100 $(PYTHON_FILES)
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

ONTOLOGY_SHEETS = core host isotype light_chain heavy_chain_germline assay parameter qualitative_measure
SHEETS = prefix field $(ONTOLOGY_SHEETS)
SHEET_TSVS = $(foreach o,$(SHEETS),ontology/$(o).tsv)

build/CoVIC-DB.xlsx: | build
	curl -L -o $@ "https://docs.google.com/spreadsheets/d/11ItLLoXY7_r2lDazY4prMERHMb-7czrim91UABnvbYM/export?format=xlsx"

$(SHEET_TSVS): build/CoVIC-DB.xlsx
	xlsx2csv --ignoreempty --delimiter tab --sheetname $(basename $(notdir $@)) $< > $@


### Ontology

build/imports.owl: $(foreach o,$(ONTOLOGY_SHEETS),ontology/$(o).tsv) | build/robot.jar
	$(ROBOT) template \
	$(foreach o,$(ONTOLOGY_SHEETS),--template ontology/$(o).tsv) \
	--output $@

build/ontology.owl: build/imports.owl ontology/protein-tree.owl | build/robot.jar
	$(ROBOT) merge \
	$(foreach o,$^,--input $(o)) \
	--output $@

.PHONY: ontology
ontology: build/ontology.owl

build/labels.tsv: build/imports.owl | build/robot.jar
	$(ROBOT) export \
	--input $< \
	--header "ID|LABEL" \
	--export $@

src/covicdbtools/config.json: src/covicdbtools/config.py $(SHEET_TSVS) build/labels.tsv
	python $^ $@

src/covicdbtools/cli.py: src/covicdbtools/config.json

.PHONY: config
config:
	touch src/covicdbtools/config.py
	make src/covicdbtools/config.json

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
examples/spr-submission.xlsx \
examples/spr-submission-valid.xlsx \
build/spr-submission-valid-expanded.tsv \
build/spr-submission-valid-expanded.html \
examples/spr-submission-invalid.xlsx \
examples/spr-submission-invalid-highlighted.xlsx \
build/spr-submission-invalid-highlighted.html

examples/%-submission.xlsx: | src/covicdbtools/cli.py
	$(CVDB) fill $* "" $@

examples/%-submission-valid.xlsx: examples/%-submission-valid.tsv | src/covicdbtools/cli.py
	$(CVDB) fill $* $< $@

examples/%-submission-invalid.xlsx: examples/%-submission-invalid.tsv | src/covicdbtools/cli.py
	$(CVDB) fill $* $< $@

examples/%-submission-invalid-highlighted.xlsx: examples/%-submission-invalid.xlsx | src/covicdbtools/cli.py
	-$(CVDB) validate $* $< $@

build/%-submission-invalid-highlighted.html: examples/%-submission-invalid.xlsx | src/covicdbtools/cli.py build
	-$(CVDB) validate $* $< $@

build/%-submission-valid-expanded.tsv: examples/%-submission-valid.xlsx | src/covicdbtools/cli.py build
	$(CVDB) expand $< $@

build/%-submission-valid-expanded.html: examples/%-submission-valid.xlsx | src/covicdbtools/cli.py build
	$(CVDB) expand $< $@

.PHONY: examples
examples: $(ANTIBODIES_EXAMPLES) $(DATASETS_EXAMPLES)



### Views

build/antibodies.tsv: tests/submit-antibodies/data/staging/antibodies.tsv | build
	$(CVDB) expand $< $@

build/antibodies.html: build/antibodies.tsv | src/covicdbtools/cli.py
	$(CVDB) convert $< $@

build/datasets/%/dataset.html: src/covicdbtools/datasets.py templates/dataset.html tests/submit-assays/data/staging/datasets/%/ | build/datasets
	mkdir -p build/datasets/$*
	python $^ $@

build/summary.html: src/covicdbtools/summaries.py templates/grid.html build/antibodies.tsv build
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

