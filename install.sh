#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
target_dir="${OPENCLAW_SKILLS_DIR:-$HOME/.openclaw/skills}/music-composer"

mkdir -p "$(dirname "$target_dir")"
rm -rf "$target_dir"
cp -R "$repo_dir" "$target_dir"

echo "Installed music_composer to $target_dir"
echo "Run: openclaw skills list"
