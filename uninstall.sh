#!/usr/bin/env bash
set -euo pipefail

SKILLS_DIR="$(cd "$(dirname "$0")/skills" && pwd)"
TARGETS=(
  "${CODEX_SKILLS_DIR:-$HOME/.codex/skills}"
  "${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
)

usage() {
  cat <<'EOF'
Usage:
  ./uninstall.sh <skill> [skill...]
  ./uninstall.sh --all

Removes repo-managed skills from Codex and Claude skill directories when present.
EOF
}

if [ "$#" -eq 0 ]; then
  usage
  exit 1
fi

remove_skill() {
  local name="$1"
  local found=0

  if [ ! -d "$SKILLS_DIR/$name" ]; then
    echo "Error: skill '$name' not found in skills/" >&2
    exit 1
  fi

  for target in "${TARGETS[@]}"; do
    if [ -d "$target/$name" ] || [ -L "$target/$name" ]; then
      rm -rf "$target/$name"
      echo "Removed: $target/$name"
      found=1
    fi
  done

  if [ "$found" -eq 0 ]; then
    echo "Not installed: $name"
  fi
}

if [ "$1" = "--all" ]; then
  for d in "$SKILLS_DIR"/*/; do
    remove_skill "$(basename "$d")"
  done
  exit 0
fi

for name in "$@"; do
  remove_skill "$name"
done
