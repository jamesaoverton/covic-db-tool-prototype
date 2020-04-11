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

ROOT="$(pwd)/"
TEMP="${ROOT}temp/"
export CVDB_STAGING="${TEMP}staging/"
export CVDB_SECRET="${TEMP}secret/"
export CVDB_PUBLIC="${TEMP}public/"
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

step "Create git data repositories for testing"
mkdir -p "${CVDB_STAGING}"
cd "${CVDB_STAGING}"
git init
mkdir -p "${CVDB_SECRET}"
mkdir -p "${CVDB_PUBLIC}"
cd "${CVDB_PUBLIC}"
git init
cd "${ROOT}"

cd "${CVDB_STAGING}"
assert "staging: directory should be empty" \
"$(tree)" \
".

0 directories, 0 files"
assert "stagin: git log should be empty" \
"$(git log)" \
""

cd "${CVDB_PUBLIC}"
assert "public: directory should be empty" \
"$(tree)" \
".

0 directories, 0 files"
assert "public: git log should be empty" \
"$(git log)" \
""
cd "${ROOT}"


step "Submit antibodies"
#${CVDB} submit antibodies ${EXAMPLES}/antibodies-submission-valid.xlsx

# Fake submit antibodies operations
cd "${CVDB_STAGING}"
touch antibodies.tsv
git add antibodies.tsv
git commit --author "${AUTHOR}" --message "${STEP}"
cp "${CVDB_STAGING}antibodies.tsv" "${CVDB_PUBLIC}"
cd "${CVDB_PUBLIC}"
git add antibodies.tsv
git commit --author "${AUTHOR}" --message "${STEP}"
cd "${ROOT}"

cd "${CVDB_STAGING}"
assert "staging: antibodies.tsv should exist" \
"$(tree)" \
".
└── antibodies.tsv

0 directories, 1 file"

assert "staging: git log should show one commit" \
"$(git shortlog)" \
"cvdbtools (1):
      Submit antibodies"

cd "${CVDB_PUBLIC}"
assert "public: antibodies.tsv should exist" \
"$(tree)" \
".
└── antibodies.tsv

0 directories, 1 file"

assert "public: git log should show one commit" \
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
# TODO: check repos (files and git log): staging, public
# TODO: build and check SQL tables: staging, public

#step "Promote Dataset"
#${CVDB} promote dataset 1
# TODO: check repos (files and git log): staging, public
# TODO: build and check SQL tables: staging, public

#step "Update Dataset"
#${CVDB} submit assays "${EXAMPLES}/neutralization-submission-valid-update.xlsx"
# TODO: check repos (files and git log): staging, public
# TODO: build and check SQL tables

#step "Promote Updated Dataset"
#${CVDB} promote dataset 1
# TODO: check repos (files and git log): staging, public
# TODO: build and check SQL tables: staging, public

# Clear trap to exit cleanly
trap '' INT TERM EXIT
echo "SUCCESS!!!"
