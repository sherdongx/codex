#!/usr/bin/env bash
set -euo pipefail

if [[ $# != 3 ]]; then
  echo "Usage: $0 <rust-target> <built-binary-directory> <output-directory>" >&2
  exit 1
fi
target=$1
binary_dir=$(cd "$2" && pwd)
mkdir -p "$3"
output_dir=$(cd "$3" && pwd)
repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
export CODEX_REPO_ROOT="$repo_root"
case "$target" in
  aarch64-apple-darwin) arch=arm64 ;;
  x86_64-apple-darwin) arch=x86_64 ;;
  *) echo "Unsupported macOS target: $target" >&2; exit 1 ;;
esac
commit=$(git -C "$repo_root" rev-parse HEAD)
name="codex-suggest-macos-${arch}-${commit:0:12}"
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
package_dir="$stage/$name"

python3 "$repo_root/scripts/build_codex_package.py" \
  --target "$target" --variant codex --cargo-profile release \
  --entrypoint-bin "$binary_dir/codex" \
  --code-mode-host-bin "$binary_dir/codex-code-mode-host" \
  --package-dir "$package_dir"

for binary in codex codex-code-mode-host; do
  codesign --force --sign - \
    --entitlements "$repo_root/.github/scripts/macos-signing/$binary.entitlements.plist" \
    "$package_dir/bin/$binary"
done
for resource in codex-path/rg codex-resources/zsh/bin/zsh; do
  codesign --force --sign - "$package_dir/$resource"
done
for executable in bin/codex bin/codex-code-mode-host codex-path/rg codex-resources/zsh/bin/zsh; do
  binary="$package_dir/$executable"
  lipo "$binary" -verify_arch "$arch"
  codesign --verify --strict "$binary"
  xcrun vtool -show-build "$binary"
  # Archives must not depend on Homebrew or other build-runner library paths.
  otool -L "$binary"
  otool -L "$binary" | awk 'NR > 1 && $1 !~ /^\/usr\/lib\// && $1 !~ /^\/System\/Library\// { bad = 1 } END { exit bad }'
done

printf '%s\n' "$arch" > "$package_dir/ARCHITECTURE"
printf 'Source: https://github.com/sherdongx/codex\nCommit: %s\nTarget: %s\nMinimum macOS: 15\n' \
  "$commit" "$target" > "$package_dir/BUILD.txt"
cp "$repo_root/scripts/macos/install-codex-suggest.sh" "$package_dir/install.sh"
chmod 755 "$package_dir/install.sh"
cp "$repo_root/docs/prompt-suggestions-macos.md" "$package_dir/README.md"
cp "$repo_root/LICENSE" "$repo_root/NOTICE" "$package_dir/"

archive="$output_dir/$name.tar.gz"
COPYFILE_DISABLE=1 tar -czf "$archive" -C "$stage" "$name"
(cd "$output_dir" && shasum -a 256 "$name.tar.gz" > "$name.tar.gz.sha256")

# Verify the distributed bytes, including installation into a path with spaces.
mkdir "$stage/extracted"
tar -xzf "$archive" -C "$stage/extracted"
prefix="$stage/install prefix"
"$stage/extracted/$name/install.sh" "$prefix"
"$prefix/bin/codex-suggest" --version
"$prefix/bin/codex-suggest" --help
"$prefix/bin/codex-suggest" features list
installed="$prefix/share/codex-prompt-suggestions"
"$installed/bin/codex-code-mode-host" --help
"$installed/codex-path/rg" --version
"$installed/codex-resources/zsh/bin/zsh" -fc 'print -r -- codex-suggest-zsh-ok'
printf 'Verified archive: %s\n' "$archive"
