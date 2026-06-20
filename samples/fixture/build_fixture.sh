#!/usr/bin/env bash
# Build a self-contained git repo fixture with a planted bug at a KNOWN commit,
# so aidbg's git-blame attribution can be verified against ground truth.
#
#   commit 1 (Alice Designer) : correct mixed-signal mux (reset drives selects low)
#   commit 2 (Bob Hotfix)     : the bug — reset forces both selects high
#
# Usage: build_fixture.sh [TARGET_DIR]   (default: /tmp/aidbg_fixture)
# Prints the target dir on stdout.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
TARGET="${1:-/tmp/aidbg_fixture}"

rm -rf "$TARGET"; mkdir -p "$TARGET"
cd "$TARGET"
git init -q
git config user.name aidbg-fixture
git config user.email fixture@example.com

# commit 1: good design (Alice)
cp -r "$HERE/design/." .
git add -A
GIT_AUTHOR_NAME="Alice Designer"  GIT_AUTHOR_EMAIL="alice@example.com" \
GIT_COMMITTER_NAME="Alice Designer" GIT_COMMITTER_EMAIL="alice@example.com" \
  git commit -q -m "Initial mixed-signal mux: RTL ctrl + extracted analog netlist + UVM TB"

# commit 2: the planted bug (Bob)
cp "$HERE/bug/ctrl.sv" rtl/ctrl.sv
git add -A
GIT_AUTHOR_NAME="Bob Hotfix"  GIT_AUTHOR_EMAIL="bob@example.com" \
GIT_COMMITTER_NAME="Bob Hotfix" GIT_COMMITTER_EMAIL="bob@example.com" \
  git commit -q -m "ctrl: force sel0/sel1 high during reset to silence X (WRONG hotfix)"

# simulation outputs (not design source) — placed for aidbg to read
mkdir -p sim
cp "$HERE/sim/wave.txt" "$HERE/sim/uvm.log" sim/

echo "$TARGET"
