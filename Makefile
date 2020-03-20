
.PHONY: all
all: build/datasets/1/dataset.html build/index.html

.PHONY: tidy
tidy:
	rm -rf build/datasets
	rm -f build/index.html build/labels.tsv

build build/datasets:
	mkdir -p $@

build/labels.tsv: ontology/imports.tsv
	sed '2d' $< \
	| cut -f1-2 \
	> $@

build/datasets/%/dataset.html: src/view-dataset.py templates/dataset.html ontology/prefixes.tsv build/labels.tsv data/datasets/% | build/datasets
	mkdir -p build/datasets/$*
	python $^ $@

build/index.html: src/build-index.py templates/index.html | build
	python $^ $@
