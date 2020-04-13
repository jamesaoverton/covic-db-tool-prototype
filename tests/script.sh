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
TEMP="${ROOT}/temp"
export CVDB_SECRET="${TEMP}/secret"
export CVDB_STAGING="${TEMP}/staging"
export CVDB_PUBLIC="${TEMP}/public"
EXAMPLES="${ROOT}/examples"
CVDB=src/covicdbtools/cli.py

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
mkdir -p "${CVDB_SECRET}"
cd "${CVDB_SECRET}"
git init
mkdir -p "${CVDB_STAGING}"
cd "${CVDB_STAGING}"
git init
mkdir -p "${CVDB_PUBLIC}"
cd "${CVDB_PUBLIC}"
git init
cd "${ROOT}"


step "Submit antibodies invalid"
assert "submission should fail" \
"$(${CVDB} submit "Shane Crotty" "shane@lji.org" "antibodies" "${EXAMPLES}/antibodies-submission-invalid.xlsx")" \
"There were 6 errors
Error in row 3: Missing required value for 'Antibody name'
Error in row 6: Missing required value for 'Host'
Error in row 6: 'Ig1' is not a recognized value for 'Isotype'
Error in row 8: 'Mus musclus' is not a recognized value for 'Host'
Error in row 8: 'Igm' is not a recognized value for 'Isotype'
Error in row 9: Duplicate value 'C3' is not allowed for 'Antibody name'"


step "Submit antibodies valid"
${CVDB} submit "Shane Crotty" "shane@lji.org" "antibodies" "${EXAMPLES}/antibodies-submission-valid.xlsx"

cd "${CVDB_SECRET}"
assert "secret: antibodies.tsv should exist" \
"$(tree)" \
".
└── antibodies.tsv

0 directories, 1 file"

assert "secret: git log should show one commit" \
"$(git shortlog)" \
"Shane Crotty (1):
      Submit antibodies"

cd "${CVDB_STAGING}"
assert "staging: antibodies.tsv should exist" \
"$(tree)" \
".
└── antibodies.tsv

0 directories, 1 file"

assert "staging: git log should show one commit" \
"$(git shortlog)" \
"Shane Crotty (1):
      Submit antibodies"

cd "${CVDB_PUBLIC}"
assert "public: antibodies.tsv should exist" \
"$(tree)" \
".
└── antibodies.tsv

0 directories, 1 file"

assert "public: git log should show one commit" \
"$(git shortlog)" \
"CoVIC (1):
      Submit antibodies"

cd "${ROOT}"


step "Create Dataset"
assert "staging: dataset 1 created" \
"$(${CVDB} create "Jon Yewdell" "jyewdell@niaid.nih.gov" "neutralization")" \
"Created dataset 1"

cd "${CVDB_SECRET}"
assert "secret: files not changed" \
"$(tree)" \
".
└── antibodies.tsv

0 directories, 1 file"

assert "secret: git log not changed" \
"$(git shortlog)" \
"Shane Crotty (1):
      Submit antibodies"

cd "${CVDB_STAGING}"
assert "staging: dataets/1/dataset.yml should exist" \
"$(tree)" \
".
├── antibodies.tsv
└── datasets
    └── 1
        └── dataset.yml

2 directories, 2 files"

assert "staging: git log should show two commits" \
"$(git shortlog)" \
"Jon Yewdell (1):
      Create dataset 1

Shane Crotty (1):
      Submit antibodies"

cd "${CVDB_PUBLIC}"
assert "public: files not changed" \
"$(tree)" \
".
└── antibodies.tsv

0 directories, 1 file"

assert "public: git log not changed" \
"$(git shortlog)" \
"CoVIC (1):
      Submit antibodies"

cd "${ROOT}"
# TODO: fetch .xlsx for dataset
# TODO: check .xlsx


step "Submit Invalid Assays"
assert "submission should fail" \
"$(${CVDB} submit "Jon Yewdell" "jyewdell@niaid.nih.gov" 1 "${EXAMPLES}/neutralization-submission-invalid.xlsx")" \
"There were 5 errors
Error in row 2: Missing required value for 'Antibody name'
Error in row 3: Duplicate value 'COVIC 1' is not allowed for 'Antibody name'
Error in row 5: 'postive' is not a recognized value for 'Qualitative measure'
Error in row 5: 'none' is not of type 'float' in 'Titer'
Error in row 6: 'intermediate' is not a recognized value for 'Qualitative measure'"


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
