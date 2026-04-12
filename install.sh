#!/usr/bin/env bash
set -euo pipefail

TARGET="${CODEX_SKILLS_DIR:-${CLAUDE_SKILLS_DIR:-$HOME/.codex/skills}}"
SKILLS_DIR="$(cd "$(dirname "$0")/skills" && pwd)"

if [ ! -d "$TARGET" ]; then
  echo "Creating $TARGET"
  mkdir -p "$TARGET"
fi

if [ "$#" -eq 0 ]; then
  # Install all skills
  count=0
  for d in "$SKILLS_DIR"/*/; do
    name="$(basename "$d")"
    cp -r "$d" "$TARGET/$name"
    echo "Installed: $name"
    count=$((count + 1))
  done
  echo "Done. $count skill(s) installed to $TARGET"
else
  # Install named skill(s)
  for name in "$@"; do
    src="$SKILLS_DIR/$name"
    if [ ! -d "$src" ]; then
      echo "Error: skill '$name' not found in skills/" >&2
      exit 1
    fi
    cp -r "$src" "$TARGET/$name"
    echo "Installed: $name"
  done
fi
