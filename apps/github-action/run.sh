#!/usr/bin/env bash
# Runs Rupture's path-safe checks from the checked-out action directory.

set -uo pipefail

KIT="${INPUT_KIT:-auto}"
PATH_INPUT="${INPUT_PATH:-.}"
FAIL_ON="${INPUT_FAIL_ON:-high}"

ACTION_DIR="${GITHUB_ACTION_PATH:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
if [[ -d "$ACTION_DIR/kits" ]]; then
  RUPTURE_ROOT="$ACTION_DIR"
elif [[ -d "$ACTION_DIR/../../kits" ]]; then
  RUPTURE_ROOT="$(cd "$ACTION_DIR/../.." && pwd)"
else
  echo "::error::Could not locate Rupture kits from action path: $ACTION_DIR"
  exit 1
fi

WORKSPACE="${GITHUB_WORKSPACE:-$PWD}"
if [[ "$PATH_INPUT" = /* ]]; then
  TARGET="$PATH_INPUT"
else
  TARGET="$WORKSPACE/$PATH_INPUT"
fi

REPORT_DIR="${RUNNER_TEMP:-$PWD}"
RAW_REPORT="$REPORT_DIR/rupture-action-raw.txt"
REPORT="$REPORT_DIR/rupture-action-report.md"
: > "$RAW_REPORT"

ANY_FAILED=false
HAS_FINDINGS=false

append_note() {
  printf "\n## %s\n\n%s\n" "$1" "$2" >> "$RAW_REPORT"
}

run_check() {
  local title="$1"
  shift

  printf "\n## %s\n\n\`\`\`text\n" "$title" >> "$RAW_REPORT"
  echo "::group::$title"

  set +e
  "$@" 2>&1 | tee -a "$RAW_REPORT"
  local rc=${PIPESTATUS[0]}
  set -u

  echo "::endgroup::"
  printf "\n\`\`\`\n" >> "$RAW_REPORT"

  if [[ "$rc" -ne 0 ]]; then
    ANY_FAILED=true
    HAS_FINDINGS=true
    echo "::warning::$title reported findings or failed with exit code $rc"
  fi
}

install_kits() {
  echo "::group::Install Rupture kits"
  python -m pip install --quiet --disable-pip-version-check --no-warn-script-location \
    "$RUPTURE_ROOT/kits/al2023-gate" "$RUPTURE_ROOT/kits/python-pivot" || {
    echo "::error::Failed to install Python Rupture kits."
    exit 1
  }
  if [[ -f "$RUPTURE_ROOT/kits/lambda-lifeline/package-lock.json" ]]; then
    (cd "$RUPTURE_ROOT/kits/lambda-lifeline" && npm ci --omit=dev --quiet) || {
      echo "::error::Failed to install lambda-lifeline dependencies."
      exit 1
    }
  else
    (cd "$RUPTURE_ROOT/kits/lambda-lifeline" && npm install --omit=dev --quiet) || {
      echo "::error::Failed to install lambda-lifeline dependencies."
      exit 1
    }
  fi
  echo "::endgroup::"
}

find_files() {
  local name="$1"
  find "$TARGET" \
    -path "*/.git" -prune -o \
    -path "*/node_modules" -prune -o \
    -path "*/.venv" -prune -o \
    -path "*/venv" -prune -o \
    -path "*/__pycache__" -prune -o \
    -name "$name" -type f -print
}

run_lambda() {
  run_check "lambda-lifeline IaC runtime check" \
    node "$RUPTURE_ROOT/kits/lambda-lifeline/bin/cli.mjs" iac --path "$TARGET" --strict

  run_check "lambda-lifeline Node compatibility check" \
    node "$RUPTURE_ROOT/kits/lambda-lifeline/bin/cli.mjs" codemod --path "$TARGET" --strict

  local audited=false
  while IFS= read -r pkg; do
    audited=true
    run_check "lambda-lifeline native dependency audit: ${pkg#$WORKSPACE/}" \
      node "$RUPTURE_ROOT/kits/lambda-lifeline/bin/cli.mjs" audit --path "$(dirname "$pkg")" --strict
  done < <(find_files "package.json" | head -n 20)

  if [[ "$audited" = false ]]; then
    append_note "lambda-lifeline native dependency audit" "No package.json files found under \`$PATH_INPUT\`."
  fi
}

run_python() {
  run_check "python-pivot Python 3.12 compatibility check" \
    python -m python_pivot.cli codemod "$TARGET" --strict

  run_check "python-pivot IaC runtime check" \
    python -m python_pivot.cli iac "$TARGET" --strict

  local audited=false
  while IFS= read -r depfile; do
    audited=true
    run_check "python-pivot native wheel audit: ${depfile#$WORKSPACE/}" \
      python -m python_pivot.cli audit "$depfile" --strict
  done < <(
    {
      find_files "requirements.txt"
      find_files "pyproject.toml"
      find_files "Pipfile"
    } | head -n 20
  )

  if [[ "$audited" = false ]]; then
    append_note "python-pivot native wheel audit" "No requirements.txt, pyproject.toml, or Pipfile found under \`$PATH_INPUT\`."
  fi
}

run_al2023() {
  run_check "al2023-gate Ansible AL2023 check" \
    python -m al2023_gate.cli ansible "$TARGET" --strict

  run_check "al2023-gate cloud-init AL2023 check" \
    python -m al2023_gate.cli cloudinit "$TARGET" --strict
}

install_kits

case "$KIT" in
  auto|all)
    run_lambda
    run_python
    run_al2023
    ;;
  lambda-lifeline)
    run_lambda
    ;;
  python-pivot)
    run_python
    ;;
  al2023-gate)
    run_al2023
    ;;
  *)
    ANY_FAILED=true
    HAS_FINDINGS=true
    append_note "Invalid kit" "Unknown kit \`$KIT\`. Use \`auto\`, \`all\`, \`lambda-lifeline\`, \`al2023-gate\`, or \`python-pivot\`."
    ;;
esac

SHOULD_FAIL=false
case "$FAIL_ON" in
  none|off|false)
    SHOULD_FAIL=false
    ;;
  critical)
    if grep -qi "critical" "$RAW_REPORT"; then
      SHOULD_FAIL=true
    fi
    ;;
  low|medium|high)
    SHOULD_FAIL="$ANY_FAILED"
    ;;
  *)
    SHOULD_FAIL=true
    append_note "Invalid fail-on threshold" "Unknown fail-on threshold \`$FAIL_ON\`. Use \`low\`, \`medium\`, \`high\`, \`critical\`, or \`none\`."
    ;;
esac

STATUS="passed"
if [[ "$SHOULD_FAIL" = true ]]; then
  STATUS="failed"
elif [[ "$HAS_FINDINGS" = true ]]; then
  STATUS="completed with findings"
fi

{
  echo "# Rupture AWS Deprecation Check"
  echo
  echo "- Kit: \`$KIT\`"
  echo "- Path: \`$PATH_INPUT\`"
  echo "- Threshold: \`$FAIL_ON\`"
  echo "- Status: \`$STATUS\`"
  echo
  echo "<details>"
  echo "<summary>Scan output</summary>"
  echo
  head -c 50000 "$RAW_REPORT"
  echo
  echo "</details>"
  echo
  echo "[Full audit report](https://ntoledo319.github.io/Rupture/audit) · [Migration Pack](https://ntoledo319.github.io/Rupture/pack)"
} > "$REPORT"

if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  cat "$REPORT" >> "$GITHUB_STEP_SUMMARY"
fi

{
  echo "report_path=$REPORT"
  echo "should_fail=$SHOULD_FAIL"
  echo "has_findings=$HAS_FINDINGS"
} >> "${GITHUB_OUTPUT:-/dev/null}"

if [[ "$SHOULD_FAIL" = true ]]; then
  echo "::warning::Rupture found deprecation risks at or above the configured threshold."
else
  echo "Rupture check completed without failing the configured threshold."
fi
