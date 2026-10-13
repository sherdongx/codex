#!/usr/bin/env bash
set -euo pipefail

if [[ ${GITHUB_ACTIONS:-} != true || $(id -u) == 0 ]]; then
  echo "Run this native installation test as the unprivileged disposable GitHub runner user." >&2
  exit 1
fi
if [[ $# != 1 ]]; then
  echo "Usage: $0 <deb-package>" >&2
  exit 1
fi
deb=$(realpath "$1")
repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
profile=/etc/apparmor.d/usr.lib.codex-suggest.codex-resources.bwrap
test ! -e /usr/bin/codex-suggest
test ! -d /usr/lib/codex-suggest
test ! -e "$profile"
if sudo grep -q '^codex-suggest-bwrap ' /sys/kernel/security/apparmor/profiles; then
  echo "An existing codex-suggest profile is present; refusing to replace it." >&2
  exit 1
fi
setting_before=$(sysctl -n kernel.apparmor_restrict_unprivileged_userns)
temporary=$(mktemp -d)
snapshot="$temporary/profile"
cleanup() {
  status=$?
  if ! sudo apt-get purge -y codex-suggest; then status=1; fi
  # Standard package removal leaves active kernel profiles alone. This CI-only
  # cleanup runs after all test processes have exited on the disposable runner.
  if [[ -f "$snapshot" ]]; then
    if ! sudo apparmor_parser -R "$snapshot"; then status=1; fi
  fi
  if [[ $(sysctl -n kernel.apparmor_restrict_unprivileged_userns) != "$setting_before" ]]; then status=1; fi
  if [[ -e /usr/bin/codex-suggest || -e "$profile" || -d /usr/lib/codex-suggest ]]; then status=1; fi
  rm -rf "$temporary"
  exit "$status"
}
trap cleanup EXIT
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "$deb"
cp "$profile" "$snapshot"
sudo grep '^codex-suggest-bwrap ' /sys/kernel/security/apparmor/profiles
test "$(stat -c '%u:%g:%a' /usr/lib/codex-suggest/codex-resources/bwrap)" = 0:0:755
test ! -w /usr/lib/codex-suggest/codex-resources/bwrap
/usr/bin/codex-suggest --version
bash "$repo_root/scripts/linux/check-bundled-sandbox.sh" /usr/lib/codex-suggest
test "$(sysctl -n kernel.apparmor_restrict_unprivileged_userns)" = "$setting_before"
echo 'Verified installed Debian sandbox and unchanged global namespace policy.'
