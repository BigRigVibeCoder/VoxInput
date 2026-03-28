#!/usr/bin/env bash
# resolve_darkgravity.sh — Source this file to set DARKGRAVITY_HOME.
#
# Priority order:
#   1. .agent/darkgravity.conf  (machine-local config written by /darkgravity_setup)
#   2. $DARKGRAVITY_HOME env var (power-user override)
#   3. Sibling directory search  (auto-detect git clone next to this project)
#   4. ~/.darkgravity-engine/    (legacy default / fresh clone location)
#
# Usage (from a workflow step):
#   PROJECT_ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null \
#     || dirname "$(dirname "$(realpath "${BASH_SOURCE[0]}")")")"
#   source "$PROJECT_ROOT/bin/resolve_darkgravity.sh" || exit 1
#
# On success: DARKGRAVITY_HOME is set and exported.
# On failure: prints a clear error and returns 1.

_dg_resolve() {
  local project_root
  project_root="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null \
    || dirname "$(dirname "$(realpath "${BASH_SOURCE[0]}")")")"

  local conf_file="$project_root/.agent/darkgravity.conf"

  # ── 1. Config file (written by /darkgravity_setup) ──────────────────────────
  if [[ -f "$conf_file" ]]; then
    local conf_val
    conf_val="$(grep -E '^DARKGRAVITY_HOME=' "$conf_file" | head -1 | cut -d= -f2-)"
    if [[ -n "$conf_val" && -f "$conf_val/bin/run_pipeline.sh" ]]; then
      export DARKGRAVITY_HOME="$conf_val"
      return 0
    fi
  fi

  # ── 2. Environment variable ──────────────────────────────────────────────────
  if [[ -n "$DARKGRAVITY_HOME" && -f "$DARKGRAVITY_HOME/bin/run_pipeline.sh" ]]; then
    export DARKGRAVITY_HOME
    return 0
  fi

  # ── 3. Sibling directory search ──────────────────────────────────────────────
  local parent_dir
  parent_dir="$(dirname "$project_root")"
  local sibling_candidates=(
    "$parent_dir/darkgravity"
    "$parent_dir/darkgravity-engine"
    "$HOME/darkgravity"
    "$HOME/Documents/darkgravity"
    "$HOME/Projects/darkgravity"
    "$HOME/dev/darkgravity"
  )
  for candidate in "${sibling_candidates[@]}"; do
    if [[ -f "$candidate/bin/run_pipeline.sh" ]]; then
      export DARKGRAVITY_HOME="$candidate"
      return 0
    fi
  done

  # ── 4. Legacy default ────────────────────────────────────────────────────────
  local legacy="$HOME/.darkgravity-engine"
  if [[ -f "$legacy/bin/run_pipeline.sh" ]]; then
    export DARKGRAVITY_HOME="$legacy"
    return 0
  fi

  # ── Not found ────────────────────────────────────────────────────────────────
  echo ""
  echo "╔══════════════════════════════════════════════════════════════════╗"
  echo "║  DarkGravity engine not found.                                   ║"
  echo "║                                                                   ║"
  echo "║  Run /darkgravity_setup to locate or install it.                 ║"
  echo "║                                                                   ║"
  echo "║  Or set DARKGRAVITY_HOME manually:                               ║"
  echo "║    export DARKGRAVITY_HOME=/path/to/your/darkgravity             ║"
  echo "╚══════════════════════════════════════════════════════════════════╝"
  echo ""
  return 1
}

_dg_resolve
