#!/usr/bin/env bash
set -e

TARGET="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
SKILLS_DIR="$(cd "$(dirname "$0")/skills" && pwd)"

if [ ! -d "$TARGET" ]; then
  echo "Creating $TARGET"
  mkdir -p "$TARGET"
fi

if [ -z "$1" ]; then
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
