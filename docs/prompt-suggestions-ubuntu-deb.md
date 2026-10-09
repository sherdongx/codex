# codex-suggest for Ubuntu (.deb)

This community Codex CLI build adds optional next-prompt suggestions using low
reasoning effort. The Debian package supports **Ubuntu 24.04 or newer on
Intel/AMD 64-bit (amd64/x86_64)**. Ubuntu 22.04 is not supported because the
bundled patched zsh requires glibc 2.38 or newer.

## Install and start

Download `codex-suggest_0.161.0+suggest.1_amd64.deb` and its matching `.sha256` file.
In the download directory, run:

```sh
sha256sum -c codex-suggest_0.161.0+suggest.1_amd64.deb.sha256
sudo apt install ./codex-suggest_0.161.0+suggest.1_amd64.deb
/usr/bin/codex-suggest login
/usr/bin/codex-suggest
```

Sign in with your own account. The package installs its command in `/usr/bin`
and its bundled executables in `/usr/lib/codex-suggest`. It preserves the ordinary
`codex` command and your existing `~/.codex` configuration and login data.
Ubuntu's package manager installs the declared dependencies when needed.
An earlier user-local launcher may take precedence on your PATH. Use
`/usr/bin/codex-suggest` explicitly to select this Debian package; installation
does not remove user-local files.

After a response, Tab or Right Arrow moves a dim suggestion into the editable
prompt; Enter sends it and Escape dismisses it. Each suggestion consumes an
additional model request. Disable suggestions for one run with
`codex-suggest -c tui.prompt_suggestions=false`.

## Sandbox permissions

The package installs an AppArmor profile for its root-owned bubblewrap helper.
It grants the application-specific user-namespace permission described in
[Ubuntu's namespace-policy documentation](https://documentation.ubuntu.com/release-notes/24.04/#unprivileged-user-namespace-restrictions),
without changing the system-wide restriction or disabling Codex's sandbox.
Administrator changes to the profile are preserved as Debian conffiles.

Where AppArmor is inactive or its kernel interface is unavailable, such as some
containers, installation succeeds without loading the profile. If sandbox
startup is blocked by local policy, ask your administrator to check the installed
profile and namespace availability. Do not disable the sandbox as a workaround.

## Update and remove

Close running instances before installing a newer package with `sudo apt install
./new-package.deb`, then start `codex-suggest` again.

```sh
sudo apt remove codex-suggest
# Or also remove the package's AppArmor configuration:
sudo apt purge codex-suggest
```

Both operations preserve your `~/.codex` data. Removal retains administrator
AppArmor configuration; purge removes this package's policy files and caches.
As with Ubuntu's standard AppArmor packaging helper, package removal does not
forcibly unload a kernel profile used by an existing process.

## Build provenance

`/usr/lib/codex-suggest/BUILD.txt` identifies the compiled payload source and its
sandbox-helper digest. `PACKAGING.txt` identifies the Debian packaging source.
The package includes the CLI, code-mode host, bubblewrap, ripgrep, patched zsh,
and license notices. CLI and helper startup tests do not sign into an account
or send model requests.
