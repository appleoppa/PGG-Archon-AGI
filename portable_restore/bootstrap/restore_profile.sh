#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_HOME="${TARGET_HOME:-$HOME}"
HERMES_DIR="$TARGET_HOME/.hermes"
PROFILE_SRC="$ROOT/profile"
mkdir -p "$HERMES_DIR/memories" "$HERMES_DIR/data" "$HERMES_DIR/skills"
backup_dir="$HERMES_DIR/backups/portable-restore-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$backup_dir"
for rel in SOUL.md memories/MEMORY.md memories/USER.md data/EVOLUTION_MANIFEST.json; do
  if [ -e "$HERMES_DIR/$rel" ]; then
    mkdir -p "$backup_dir/$(dirname "$rel")"
    cp -a "$HERMES_DIR/$rel" "$backup_dir/$rel"
  fi
done
cp -a "$PROFILE_SRC/SOUL.md" "$HERMES_DIR/SOUL.md"
cp -a "$PROFILE_SRC/memories/MEMORY.md" "$HERMES_DIR/memories/MEMORY.md"
cp -a "$PROFILE_SRC/memories/USER.md" "$HERMES_DIR/memories/USER.md"
cp -a "$PROFILE_SRC/data/EVOLUTION_MANIFEST.json" "$HERMES_DIR/data/EVOLUTION_MANIFEST.json"
rsync -a --delete "$PROFILE_SRC/skills/" "$HERMES_DIR/skills/"
echo "RESTORE_OK target=$HERMES_DIR backup=$backup_dir"
