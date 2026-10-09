#!/bin/sh
set -eu

if [ "$#" -gt 1 ]; then
  echo "Usage: $0 [installation-prefix; default: ~/.local]" >&2
  exit 1
fi
package_dir=$(CDPATH= cd "$(dirname "$0")" && pwd)
prefix=${1:-"$HOME/.local"}

if [ "$(uname -s)" != Linux ]; then
  echo "This package requires Linux x86_64." >&2
  exit 1
fi
arch=$(cat "$package_dir/ARCHITECTURE")
if [ "$(uname -m)" != "$arch" ]; then
  echo "This package is for $arch; download the package matching $(uname -m)." >&2
  exit 1
fi
libc=$(getconf GNU_LIBC_VERSION 2>/dev/null) || {
  echo "This package requires Ubuntu 24.04 or newer (glibc 2.38+)." >&2
  exit 1
}
version=${libc#glibc }
major=${version%%.*}
minor=${version#*.}
minor=${minor%%.*}
if [ "$major" -lt 2 ] || { [ "$major" -eq 2 ] && [ "$minor" -lt 38 ]; }; then
  echo "This package requires glibc 2.38 or newer (found $libc)." >&2
  exit 1
fi
for executable in bin/codex bin/codex-code-mode-host codex-resources/bwrap codex-path/rg codex-resources/zsh/bin/zsh; do
  if [ ! -x "$package_dir/$executable" ]; then
    echo "Incomplete package: missing executable $executable" >&2
    exit 1
  fi
done
for file in codex-package.json BUILD.txt README.md LICENSE NOTICE; do
  if [ ! -f "$package_dir/$file" ]; then
    echo "Incomplete package: missing file $file" >&2
    exit 1
  fi
done

destination="$prefix/share/codex-prompt-suggestions"
mkdir -p "$prefix/bin" "$destination"
for entry in bin codex-path codex-resources codex-package.json ARCHITECTURE BUILD.txt README.md LICENSE NOTICE; do
  cp -R "$package_dir/$entry" "$destination/"
done
cat > "$prefix/bin/codex-suggest" <<'LAUNCHER'
#!/bin/sh
set -eu
launcher_dir=$(CDPATH= cd "$(dirname "$0")" && pwd)
export RUST_LOG="${RUST_LOG:-off}"
exec "$launcher_dir/../share/codex-prompt-suggestions/bin/codex" \
  --no-daemon -c tui.prompt_suggestions=true "$@"
LAUNCHER
chmod 755 "$prefix/bin/codex-suggest"
printf 'Installed codex-suggest. Run: "%s/bin/codex-suggest"\n' "$prefix"
printf 'If needed, add "%s/bin" to your PATH.\n' "$prefix"
