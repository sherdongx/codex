#!/usr/bin/env bash
set -euo pipefail

if [[ $# != 1 ]]; then
  echo "Usage: $0 <extracted-package>" >&2
  exit 1
fi
package_dir=$(cd "$1" && pwd)
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
mkdir "$stage/work" "$stage/read-only" "$stage/empty-path"
printf 'untouched\n' > "$stage/read-only/sentinel"
config=(-c 'sandbox_mode="workspace-write"'
  -c 'sandbox_workspace_write.exclude_slash_tmp=true'
  -c 'sandbox_workspace_write.exclude_tmpdir_env_var=true')

# An empty PATH forces the bundled helper, even if the runner has system bwrap.
(cd "$stage/work" && PATH="$stage/empty-path" "$package_dir/bin/codex" \
  "${config[@]}" sandbox -- /bin/sh -c \
  'printf "allowed\n" > allowed; if printf "changed\n" > "$1" 2>/dev/null; then exit 23; fi' \
  sh "$stage/read-only/sentinel")
test "$(cat "$stage/work/allowed")" = allowed
test "$(cat "$stage/read-only/sentinel")" = untouched

# Changing a disposable copy must fail at digest verification, before execution.
cp -R "$package_dir" "$stage/tampered"
printf x >> "$stage/tampered/codex-resources/bwrap"
set +e
(cd "$stage/work" && PATH="$stage/empty-path" "$stage/tampered/bin/codex" \
  "${config[@]}" sandbox -- /bin/true) > "$stage/tamper.log" 2>&1
result=$?
set -e
cat "$stage/tamper.log"
test "$result" = 8
grep -q 'bundled bubblewrap digest mismatch' "$stage/tamper.log"
echo 'Verified bundled sandbox restrictions and helper integrity.'
