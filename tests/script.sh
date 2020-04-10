#!/usr/bin/env bash

# Don't worry about
# - managing users
# - managing inventory
# - logging stuff
# - keeping secrets

# http://redsymbol.net/articles/unofficial-bash-strict-mode/
set -euo pipefail
IFS=$'\n\t'

### Initialization

ROOT="$(pwd)"
TEMP="temp/"
export CVDB_DATA_REPO="${TEMP}data_repo/"
#EXAMPLE="examples/"
#CVDB="src/covicdbtools/cli.py"
AUTHOR="cvdbtools <cvdb@example.com>"

step() {
  STEP="$1"
  echo "${STEP}"
}

MESSAGE=""
assert() {
  MESSAGE="$1"
  diff <(echo "$2") <(echo "$3")
}

# If the script exits early, print the current step.
print_failure() {
  echo "ERROR ${MESSAGE}"
  echo "ERROR tests/script.sh stopped at: ${STEP}"
}
trap 'print_failure' INT TERM EXIT


### Script

step "Create git data repository for testing"
mkdir -p "${CVDB_DATA_REPO}"
cd "${CVDB_DATA_REPO}"
git init
assert "Directory should be empty" \
"$(tree)" \
".

0 directories, 0 files"
assert "git log should be empty" \
"$(git log)" \
""
cd "${ROOT}"


step "Submit antibodies"
#${CVDB} submit antibodies ${EXAMPLES}/antibodies-submission-valid.xlsx

# Fake submit antibodies operations
cd "${CVDB_DATA_REPO}"
touch antibodies.tsv
git add antibodies.tsv
git commit --author "${AUTHOR}" --message "${STEP}"
git checkout --orphan public
touch antibodies.tsv
git add antibodies.tsv
git commit --author "${AUTHOR}" --message "${STEP}"
git checkout master
cd "${ROOT}"

cd "${CVDB_DATA_REPO}"
git checkout master
assert "master branch: antibodies.tsv should exist" \
"$(tree)" \
".
└── antibodies.tsv

0 directories, 1 file"

assert "master branch: git log should show one commit" \
"$(git shortlog)" \
"cvdbtools (1):
      Submit antibodies"

git checkout public
assert "public branch: antibodies.tsv should exist" \
"$(tree)" \
".
└── antibodies.tsv

0 directories, 1 file"

assert "public branch: git log should show one commit" \
"$(git shortlog)" \
"cvdbtools (1):
      Submit antibodies"

# TODO: check SQL tables
cd "${ROOT}"


#step "Create Dataset"
#${CVDB} create dataset "${EXAMPLES}/dataset.yml"
# TODO: create dataset: assay type, name, etc.
# TODO: fetch .xlsx for dataset
# TODO: check .xlsx

#step "Submit Invalid Assays"
#${CVDB} submit assays "${EXAMPLES}/neutralization-submission-invalid.xlsx" > "${TEMP}/invalid.xlsx"
# TODO: check invalid output

#step "Submit Valid Assays"
#${CVDB} submit assays "${EXAMPLES}/neutralization-submission-valid.xlsx"
# TODO: check branches (files and git log): master, public
# TODO: build and check SQL tables: master, public

#step "Promote Dataset"
#${CVDB} promote dataset 1
# TODO: check branches (files and git log): master, public
# TODO: build and check SQL tables: master, public

#step "Update Dataset"
#${CVDB} submit assays "${EXAMPLES}/neutralization-submission-valid-update.xlsx"
# TODO: check branches (files and git log): master, public
# TODO: build and check SQL tables

#step "Promote Updated Dataset"
#${CVDB} promote dataset 1
# TODO: check branches (files and git log): master, public
# TODO: build and check SQL tables: master, public

# Clear trap to exit cleanly
trap '' INT TERM EXIT
echo "SUCCESS!!!"
