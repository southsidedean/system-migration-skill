#!/bin/sh
# The checks CI runs that work on your own machine. Run it before pushing:
#   scripts/check.sh
# For the lint tools, use a virtual environment: python3 -m pip install --require-hashes -r requirements-dev.txt
# A tool that isn't installed is skipped with a note here; in CI it's a failure.
set -u
cd "$(dirname "$0")/.." || exit 2

python=python3
[ -x .venv/bin/python ] && python=.venv/bin/python
failures=0

run() {
  name=$1
  shift
  if "$@" >/tmp/check.$$ 2>&1; then
    echo "PASS  $name"
  else
    echo "FAIL  $name"
    tail -20 /tmp/check.$$
    failures=$((failures + 1))
  fi
  rm -f /tmp/check.$$
}

skip() {
  if [ "${CI:-}" = true ]; then
    echo "FAIL  $1: not installed"
    failures=$((failures + 1))
  else
    echo "SKIP  $1: not installed here; CI runs it"
  fi
}

has_module() { "$python" -c "import importlib.util, sys; sys.exit(importlib.util.find_spec('$1') is None)"; }

run "script tests" "$python" scripts/test_scripts.py
run "migrate tests" "$python" scripts/test_migrate.py
run "eval fixtures" "$python" evals/test_evals.py
run "the skill is well formed" "$python" scripts/validate_skill.py

for module in ruff bandit mypy codespell_lib; do
  if has_module "$module"; then
    case "$module" in
    ruff) run ruff "$python" -m ruff check scripts evals ;;
    bandit) run bandit "$python" -m bandit -q -c pyproject.toml -r scripts ;;
    mypy) run mypy "$python" -m mypy ;;
    codespell_lib) run codespell "$python" -m codespell_lib ;;
    esac
  else
    skip "$module"
  fi
done

if command -v shellcheck >/dev/null 2>&1; then
  run shellcheck shellcheck -s sh scripts/*.sh
else
  skip shellcheck
fi

[ "$failures" = 0 ] && echo "All checks passed." || echo "$failures check(s) failed."
exit "$failures"
