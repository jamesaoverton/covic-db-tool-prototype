#!/bin/sh

# Don't worry about
# - managing users
# - managing inventory
# - logging stuff
# - keeping secrets


### Initialization

PROGNAME="$(basename "$0")"
ROOT="$(pwd)"
TEMP="${ROOT}/temp"
RESULT="${TEMP}/result"
mkdir "${TEMP}"
export CVDB_DATA="${TEMP}/data"
EXAMPLES="${ROOT}/examples"

step() {
  STEP="$1"
  echo "${STEP}"
}

fail() {
  MESSAGE="${1:-"Unknown Error"}"
  echo "${PROGNAME}: Failed at step '${STEP}'" 1>&2
  echo "${PROGNAME}: ERROR ${MESSAGE}" 1>&2
  exit 1
}

# Compare an expected string to the ${RESULT} file
check_result() {
  EXPECTED="$1"
  echo "$1" | diff - "${RESULT}" || fail "expected string differs from contents of ${RESULT}"
}

# Compare an expected log file to the actual git shortlog of a branch
check_git_log() {
  EXPECTED="$1"
  BRANCH="$2"
  EXPECTED_LOG="${EXPECTED}/${BRANCH}.log"
  ACTUAL="${CVDB_DATA}/${BRANCH}"
  (cd "${ACTUAL}" && git shortlog HEAD) | \
  diff "${EXPECTED_LOG}" - || fail "git shortlog for '${ACTUAL}' should match '${EXPECTED_LOG}'"
}

# Compare CVDB_DATA files and logs to a test directory
check_repos() {
  EXPECTED="$1"
  diff -rq --exclude=".git" "${CVDB_DATA}" "${EXPECTED}/data" || fail "'${CVDB_DATA}' should match '${EXPECTED}/data'"
  check_git_log "${EXPECTED}" secret
  check_git_log "${EXPECTED}" staging
  check_git_log "${EXPECTED}" public
}


### Script

step "Create git data repositories for testing"
cvdb initialize > "${RESULT}" || fail "Failed to initialize"
check_result "Initialized data repositories in '${CVDB_DATA}'"

tree "${CVDB_DATA}" > "${RESULT}" || fail "Failed to run tree"
check_result "${CVDB_DATA}
├── public
├── secret
└── staging

3 directories, 0 files"


step "Fetch antibodies template"
FILE="${TEMP}/antibodies-submission.xlsx"
cvdb fetch template antibodies "${FILE}" || fail "Failed to fetch"
cvdb read "${FILE}" Antibodies > "${RESULT}" || fail "Failed to read"
check_result "Empty table"


step "Submit antibodies invalid"
FILE="${EXAMPLES}/antibodies-submission-invalid.xlsx" 
cvdb submit antibodies "Shane Crotty" shane@lji.org LJI "${FILE}" \
  > "${RESULT}" && fail "Submit invalid should fail"
check_result "There were 7 errors
Error in row 3: Duplicate value 'VD-Crotty 1' is not allowed in column 'Antibody name'
Error in row 4: Missing required value in column 'Antibody name'
Error in row 5: Missing required value in column 'Host'
Error in row 6: 'IggA1' is not a valid term in column 'Isotype'
Error in row 7: 'kapa' is not a valid term in column 'Light chain'
Error in row 8: 'IGVH1-8' is not a valid term in column 'Heavy chain germline'
Error in row 9: 'top' is not of type 'integer' in column 'Structural data'"


step "Submit antibodies valid"
FILE="${EXAMPLES}/antibodies-submission-valid.xlsx" 
cvdb submit antibodies "Shane Crotty" shane@lji.org LJI "${FILE}" \
  > "${RESULT}" || fail "Failed to submit"
check_result "Submitted antibodies"
check_repos "${ROOT}/tests/submit-antibodies"


step "Create Dataset"
COLUMNS="ab_label,tested_antigen,n,obi_0001741,obi_0001741_stddev,obi_0001739,obi_0001739_stddev,obi_0001731,obi_0001731_stddev,qualitative_measure,comment"
cvdb create dataset "Jon Yewdell" jyewdell@niaid.nih.gov --columns "${COLUMNS}" \
  > "${RESULT}" || fail "Failed to create"
check_result "Created dataset 1"
check_repos "${ROOT}/tests/create-dataset"


step "Fetch assays template"
FILE="${TEMP}/spr-submission.xlsx"
cvdb fetch template 1 "${FILE}" || fail "Failed to fetch"
cvdb read "${FILE}" Dataset > "${RESULT}" || fail "Failed to read"
check_result "Empty table"


step "Submit Invalid Assays"
FILE="${EXAMPLES}/spr-submission-invalid.xlsx"
cvdb submit assays "Jon Yewdell" jyewdell@niaid.nih.gov 1 "${FILE}" \
  > "${RESULT}" && fail "Submit invalid should fail"
check_result "There were 3 errors
Error in row 2: 'X' is not of type 'integer' in column 'n'
Error in row 2: '7000O' is not of type 'float_threshold_na' in column 'Standard deviation in M^-1s^-1'
Error in row 2: 'Positive' is not a valid term in column 'Qualitiative measure'"


step "Submit Valid Assays"
FILE="${EXAMPLES}/spr-submission-valid.xlsx"
cvdb submit assays "Jon Yewdell" jyewdell@niaid.nih.gov 1 "${FILE}" \
  > "${RESULT}" || fail "Failed to submit"
check_result "Submitted assays to dataset 1"
check_repos "${ROOT}/tests/submit-assays"


step "Promote Dataset"
cvdb promote dataset "Sharon Schendel" "schendel@lji.org" 1 \
  > "${RESULT}" || faile "Failed to promote"
check_result "Promoted dataset 1 from staging to public"
check_repos "${ROOT}/tests/promote-dataset"


#step "Update Dataset"
#cvdb submit assays "${EXAMPLES}/neutralization-submission-valid-update.xlsx"
# TODO: check repos (files and git log): staging, public
# TODO: build and check SQL tables


#step "Promote Updated Dataset"
#cvdb promote dataset 1
# TODO: check repos (files and git log): staging, public
# TODO: build and check SQL tables: staging, public

echo "SUCCESS!!!"
