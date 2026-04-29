#!/usr/bin/env bash
# rupture/check@v1 — entrypoint
# Runs the Rupture kits against the workspace and emits findings as
# GitHub Actions annotations + an optional PR comment.

set -euo pipefail

KIT="${INPUT_KIT:-auto}"
PATH_ARG="${INPUT_PATH:-.}"
FORMAT="${INPUT_FORMAT:-table}"
STRICT="${INPUT_STRICT:-true}"

echo "::group::Install Rupture kits"
pip install --quiet \
  "git+https://github.com/ntoledo319/Rupture.git#subdirectory=kits/al2023-gate" \
  "git+https://github.com/ntoledo319/Rupture.git#subdirectory=kits/python-pivot" || true
# lambda-lifeline is Node-based; pull npm dependency separately if needed.
echo "::endgroup::"

run_kit() {
  local kit="$1"
  echo "::group::$kit scan"
  case "$kit" in
    al2023-gate)
      al2023-gate scan --path "$PATH_ARG" --format "$FORMAT" ${STRICT:+--strict} || EXIT=$?
      ;;
    python-pivot)
      python-pivot scan --path "$PATH_ARG" --format "$FORMAT" ${STRICT:+--strict} || EXIT=$?
      ;;
    lambda-lifeline)
      if command -v lambda-lifeline >/dev/null 2>&1; then
        lambda-lifeline scan --path "$PATH_ARG" --format "$FORMAT" ${STRICT:+--strict} || EXIT=$?
      else
        echo "lambda-lifeline binary not on PATH; skipping"
      fi
      ;;
  esac
  echo "::endgroup::"
}

EXIT=0
case "$KIT" in
  auto)
    run_kit lambda-lifeline
    run_kit al2023-gate
    run_kit python-pivot
    ;;
  *)
    run_kit "$KIT"
    ;;
esac

# Annotate the PR with a one-liner.
if [ -n "${GITHUB_PR_NUMBER:-}" ] && [ -n "${GITHUB_TOKEN:-}" ]; then
  COMMENT="Rupture scan completed (kit=${KIT}, exit=${EXIT}). Full report available via the paid Audit PDF at https://ntoledo319.github.io/Rupture/audit/."
  curl -s -X POST -H "Authorization: Bearer $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/${GITHUB_REPOSITORY}/issues/${GITHUB_PR_NUMBER}/comments" \
    -d "{\"body\": \"${COMMENT}\"}" >/dev/null || true
fi

exit "$EXIT"
