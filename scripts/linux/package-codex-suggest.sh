#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C

if [[ $# != 2 ]]; then
  echo "Usage: $0 <built-binary-directory> <output-directory>" >&2
  exit 1
fi
: "${CODEX_BWRAP_SHA256:?Set the digest embedded when building codex}"
binary_dir=$(cd "$1" && pwd)
mkdir -p "$2"
output_dir=$(cd "$2" && pwd)
repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
export CODEX_REPO_ROOT="$repo_root"
target=x86_64-unknown-linux-musl
commit=$(git -C "$repo_root" rev-parse HEAD)
name="codex-suggest-ubuntu-x86_64-${commit:0:12}"
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
package_dir="$stage/$name"

printf '%s  %s\n' "$CODEX_BWRAP_SHA256" "$binary_dir/bwrap" | sha256sum -c -
python3 "$repo_root/scripts/build_codex_package.py" \
  --target "$target" --variant codex --cargo-profile release \
  --entrypoint-bin "$binary_dir/codex" \
  --code-mode-host-bin "$binary_dir/codex-code-mode-host" \
  --bwrap-bin "$binary_dir/bwrap" --package-dir "$package_dir"

for executable in bin/codex bin/codex-code-mode-host codex-resources/bwrap codex-path/rg codex-resources/zsh/bin/zsh; do
  binary="$package_dir/$executable"
  readelf -h "$binary" | grep -q 'Class:.*ELF64'
  readelf -h "$binary" | grep -q 'Machine:.*Advanced Micro Devices X86-64'
  if [[ "$executable" == codex-resources/zsh/bin/zsh ]]; then
    # The pinned upstream zsh uses Ubuntu's standard glibc/terminal libraries.
    readelf -l "$binary" | grep -q '/lib64/ld-linux-x86-64.so.2'
    readelf -d "$binary" | awk '
      /NEEDED/ && $NF !~ /^\[(libtinfo\.so\.6|libm\.so\.6|libc\.so\.6)\]$/ { bad = 1 }
      /RPATH|RUNPATH/ { bad = 1 }
      END { exit bad }'
  elif readelf -l "$binary" | grep -q INTERP || readelf -d "$binary" | grep -q NEEDED; then
    echo "Package executable must be statically linked: $executable" >&2
    exit 1
  fi
done
printf '%s  %s\n' "$CODEX_BWRAP_SHA256" "$package_dir/codex-resources/bwrap" | sha256sum -c -
printf 'x86_64\n' > "$package_dir/ARCHITECTURE"
printf 'Source: https://github.com/sherdongx/codex\nCommit: %s\nTarget: %s\nBwrap SHA-256: %s\n' \
  "$commit" "$target" "$CODEX_BWRAP_SHA256" > "$package_dir/BUILD.txt"
cp "$repo_root/scripts/linux/install-codex-suggest.sh" "$package_dir/install.sh"
chmod 755 "$package_dir/install.sh"
cp "$repo_root/docs/prompt-suggestions-ubuntu.md" "$package_dir/README.md"
cp "$repo_root/LICENSE" "$repo_root/NOTICE" "$package_dir/"

archive="$output_dir/$name.tar.gz"
tar -czf "$archive" -C "$stage" "$name"
(cd "$output_dir" && sha256sum "$name.tar.gz" > "$name.tar.gz.sha256")
mkdir "$stage/extracted"
tar -xzf "$archive" -C "$stage/extracted"
sh "$repo_root/scripts/linux/smoke-codex-suggest.sh" \
  "$stage/extracted/$name" "$stage/install prefix"
printf 'Verified archive: %s\n' "$archive"
