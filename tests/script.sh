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
mkdir "${TEMP}"
export CVDB_DATA="${TEMP}/data"
CVDB_SECRET="${CVDB_DATA}/secret"
CVDB_STAGING="${CVDB_DATA}/staging"
CVDB_PUBLIC="${CVDB_DATA}/public"
EXAMPLES="${ROOT}/examples"
CVDB=src/covicdbtools/cli.py

step() {
  STEP="$1"
  echo "${STEP}"
}

# Compare two strings
assert() {
  MESSAGE="$1"
  diff <(echo "$2") <(echo "$3")
  MESSAGE=""
}

# Compare CVDB_DATA files and logs to a test directory
check() {
  MESSAGE="'${CVDB_DATA}' should match '$1/data'"
  diff -rq --exclude=".git" "${CVDB_DATA}" "$1/data"
  MESSAGE="'${CVDB_DATA}' git shortlog should match '$1/*.log'"
  diff <(cd "${CVDB_SECRET}" && git shortlog HEAD) "$1/secret.log"
  diff <(cd "${CVDB_STAGING}" && git shortlog HEAD) "$1/staging.log"
  diff <(cd "${CVDB_PUBLIC}" && git shortlog HEAD) "$1/public.log"
  MESSAGE=""
}

# If the script exits early, print the current step.
print_failure() {
  echo "ERROR ${MESSAGE}"
  echo "ERROR tests/script.sh stopped at: ${STEP}"
}
trap 'print_failure' INT TERM EXIT


### Script

step "Create git data repositories for testing"
assert "submission should fail" \
  "$(${CVDB} initialize)" \
  "Initialized data repositories in '${CVDB_DATA}'"
assert "directories should be created" \
  "$(tree "${CVDB_DATA}")" \
  "${CVDB_DATA}
├── public
├── secret
└── staging

3 directories, 0 files"


step "Fetch antibodies template"
FILE="${TEMP}/antibodies-submission.xlsx"
${CVDB} fetch template antibodies "${FILE}"
assert "template should be empty" \
  "$(${CVDB} read "${FILE}" Antibodies)" \
  "Empty table"


step "Submit antibodies invalid"
assert "submission should fail" \
  "$(${CVDB} submit antibodies "Shane Crotty" "shane@lji.org" "LJI" "${EXAMPLES}/antibodies-submission-invalid.xlsx")" \
  "There were 6 errors
Error in row 3: Missing required value for 'Antibody name'
Error in row 6: Missing required value for 'Host'
Error in row 6: 'Ig1' is not a recognized value for 'Isotype'
Error in row 8: 'Mus musclus' is not a recognized value for 'Host'
Error in row 8: 'Igm' is not a recognized value for 'Isotype'
Error in row 9: Duplicate value 'C3' is not allowed for 'Antibody name'"


step "Submit antibodies valid"
assert "valid antibody submission should succeed" \
  "$(${CVDB} submit antibodies "Shane Crotty" "shane@lji.org" "LJI" "${EXAMPLES}/antibodies-submission-valid.xlsx")" \
  "Submitted antibodies"
check "${ROOT}/tests/submit-antibodies"


step "Create Dataset"
assert "staging: dataset 1 created" \
  "$(${CVDB} create dataset "Jon Yewdell" "jyewdell@niaid.nih.gov" "neutralization")" \
  "Created dataset 1"
check "${ROOT}/tests/create-dataset"


step "Fetch assays template"
FILE="${TEMP}/neutralization-submission.xlsx"
${CVDB} fetch template 1 "${FILE}"
assert "template should be empty" \
  "$(${CVDB} read "${FILE}" Dataset)" \
  "Empty table"


step "Submit Invalid Assays"
assert "invalid submission should fail" \
  "$(${CVDB} submit assays "Jon Yewdell" "jyewdell@niaid.nih.gov" 1 "${EXAMPLES}/neutralization-submission-invalid.xlsx")" \
  "There were 5 errors
Error in row 2: Missing required value for 'Antibody name'
Error in row 3: Duplicate value 'COVIC 1' is not allowed for 'Antibody name'
Error in row 5: 'postive' is not a recognized value for 'Qualitative measure'
Error in row 5: 'none' is not of type 'float' in 'Titer'
Error in row 6: 'intermediate' is not a recognized value for 'Qualitative measure'"


step "Submit Valid Assays"
assert "valid submission should succeed" \
  "$(${CVDB} submit assays "Jon Yewdell" "jyewdell@niaid.nih.gov" 1 "${EXAMPLES}/neutralization-submission-valid.xlsx")" \
  "Submitted assays to dataset 1"
check "${ROOT}/tests/submit-assays"


step "Promote Dataset"
assert "promotion should succeed" \
  "$(${CVDB} promote dataset "Sharon Schendel" "schendel@lji.org" 1)" \
  "Promoted dataset 1 from staging to public"
check "${ROOT}/tests/promote-dataset"


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
