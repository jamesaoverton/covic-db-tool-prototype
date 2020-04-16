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
check_result "There were 6 errors
Error in row 3: Missing required value for 'Antibody name'
Error in row 6: Missing required value for 'Host'
Error in row 6: 'Ig1' is not a recognized value for 'Isotype'
Error in row 8: 'Mus musclus' is not a recognized value for 'Host'
Error in row 8: 'Igm' is not a recognized value for 'Isotype'
Error in row 9: Duplicate value 'C3' is not allowed for 'Antibody name'"


step "Submit antibodies valid"
FILE="${EXAMPLES}/antibodies-submission-valid.xlsx" 
cvdb submit antibodies "Shane Crotty" shane@lji.org LJI "${FILE}" \
  > "${RESULT}" || fail "Failed to submit"
check_result "Submitted antibodies"
check_repos "${ROOT}/tests/submit-antibodies"


step "Create Dataset"
cvdb create dataset "Jon Yewdell" jyewdell@niaid.nih.gov neutralization \
  > "${RESULT}" || fail "Failed to create"
check_result "Created dataset 1"
check_repos "${ROOT}/tests/create-dataset"


step "Fetch assays template"
FILE="${TEMP}/neutralization-submission.xlsx"
cvdb fetch template 1 "${FILE}" || fail "Failed to fetch"
cvdb read "${FILE}" Dataset > "${RESULT}" || fail "Failed to read"
check_result "Empty table"


step "Submit Invalid Assays"
FILE="${EXAMPLES}/neutralization-submission-invalid.xlsx"
cvdb submit assays "Jon Yewdell" jyewdell@niaid.nih.gov 1 "${FILE}" \
  > "${RESULT}" && fail "Submit invalid should fail"
check_result "There were 5 errors
Error in row 2: Missing required value for 'Antibody label'
Error in row 3: Duplicate value 'COVIC 1' is not allowed for 'Antibody label'
Error in row 5: 'postive' is not a recognized value for 'Qualitative measure'
Error in row 5: 'none' is not of type 'float' in 'Titer'
Error in row 6: 'intermediate' is not a recognized value for 'Qualitative measure'"


step "Submit Valid Assays"
FILE="${EXAMPLES}/neutralization-submission-valid.xlsx"
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
