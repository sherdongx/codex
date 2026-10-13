#!/bin/sh
set -eu

if [ "${CODEX_DEB_CONTAINER_TEST:-}" != 1 ] || [ ! -f /.dockerenv ] || [ "$(id -u)" != 0 ]; then
  echo "Run this installation test only inside its disposable root Docker container." >&2
  exit 1
fi
if [ "$#" != 1 ]; then
  echo "Usage: $0 <deb-package>" >&2
  exit 1
fi
deb=$1
profile=/etc/apparmor.d/usr.lib.codex-suggest.codex-resources.bwrap
local_profile=/etc/apparmor.d/local/usr.lib.codex-suggest.codex-resources.bwrap
export DEBIAN_FRONTEND=noninteractive
useradd -m -s /bin/sh codex-deb-test
test_home=/home/codex-deb-test
mkdir -p "$test_home/.codex" "$test_home/.local/bin"
printf 'model_reasoning_effort = "high"\n' > "$test_home/.codex/config.toml"
printf 'existing user-local launcher\n' > "$test_home/.local/bin/codex-suggest"
chown -R codex-deb-test:codex-deb-test "$test_home"
printf '#!/bin/sh\nprintf "ordinary codex preserved\\n"\n' > /usr/bin/codex
chmod 755 /usr/bin/codex
config_before=$(sha256sum "$test_home/.codex/config.toml")
launcher_before=$(sha256sum "$test_home/.local/bin/codex-suggest")
ordinary_before=$(sha256sum /usr/bin/codex)
apt-get update
apt-get install -y --no-install-recommends "$deb"
test "$(sha256sum "$test_home/.codex/config.toml")" = "$config_before"
test "$(sha256sum "$test_home/.local/bin/codex-suggest")" = "$launcher_before"
test "$(sha256sum /usr/bin/codex)" = "$ordinary_before"

su -s /bin/sh codex-deb-test -c '
  set -eu
  /usr/bin/codex-suggest --version
  /usr/bin/codex-suggest --help
  /usr/bin/codex-suggest features list
  /usr/lib/codex-suggest/bin/codex-code-mode-host --help
  /usr/lib/codex-suggest/codex-resources/bwrap --version
  /usr/lib/codex-suggest/codex-path/rg --version
  /usr/lib/codex-suggest/codex-resources/zsh/bin/zsh -fc "print -r -- deb-zsh-ok"
'
apparmor_parser --skip-kernel-load --skip-cache "$profile"
test "$(stat -c '%u:%g:%a' /usr/lib/codex-suggest/codex-resources/bwrap)" = 0:0:755

printf '\n# Administrator main-profile marker\n' >> "$profile"
printf '\n# Administrator local-profile marker\n' >> "$local_profile"
profile_before=$(sha256sum "$profile")
local_before=$(sha256sum "$local_profile")
apt-get install -y --no-install-recommends --reinstall "$deb"
test "$(sha256sum "$profile")" = "$profile_before"
test "$(sha256sum "$local_profile")" = "$local_before"
test "$(sha256sum "$test_home/.codex/config.toml")" = "$config_before"
test "$(sha256sum "$test_home/.local/bin/codex-suggest")" = "$launcher_before"
test "$(sha256sum /usr/bin/codex)" = "$ordinary_before"

apt-get remove -y codex-suggest
test ! -e /usr/bin/codex-suggest
test ! -d /usr/lib/codex-suggest
test "$(sha256sum "$profile")" = "$profile_before"
test "$(sha256sum "$local_profile")" = "$local_before"
apt-get purge -y codex-suggest
test ! -e "$profile"
test ! -e "$local_profile"
test "$(sha256sum "$test_home/.codex/config.toml")" = "$config_before"
test "$(sha256sum "$test_home/.local/bin/codex-suggest")" = "$launcher_before"
test "$(sha256sum /usr/bin/codex)" = "$ordinary_before"
echo 'Verified Debian install, reinstall, configuration preservation, remove and purge.'
