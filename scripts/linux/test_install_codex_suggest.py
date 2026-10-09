"""Exercise installation and launcher behavior for the Ubuntu portable package."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

INSTALLER = Path(__file__).with_name("install-codex-suggest.sh")


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.package = self.root / "download with spaces"
        self.package.mkdir()
        self.prefix = self.root / "install with spaces"
        shutil.copyfile(INSTALLER, self.package / "install.sh")
        self.commands = self.root / "commands"
        self.commands.mkdir()
        self.env = {**os.environ, "PATH": f"{self.commands}:{os.environ['PATH']}"}
        self.env.pop("RUST_LOG", None)
        self.mock_host()
        (self.package / "ARCHITECTURE").write_text("x86_64\n")
        for name in (
            "codex-package.json",
            "BUILD.txt",
            "README.md",
            "LICENSE",
            "NOTICE",
        ):
            (self.package / name).write_text("fixture\n")
        for name in (
            "bin/codex",
            "bin/codex-code-mode-host",
            "codex-resources/bwrap",
            "codex-path/rg",
            "codex-resources/zsh/bin/zsh",
        ):
            self.executable(
                self.package / name, '#!/bin/sh\nprintf "%s\\n" "$RUST_LOG" "$@"\n'
            )

    def executable(self, path, body):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
        path.chmod(0o755)

    def mock_host(self, system="Linux", arch="x86_64", libc="2.39"):
        self.executable(
            self.commands / "uname",
            f'#!/bin/sh\ncase "$1" in -s) echo {system};; -m) echo {arch};; esac\n',
        )
        self.executable(self.commands / "getconf", f"#!/bin/sh\necho glibc {libc}\n")

    def install(self):
        return subprocess.run(
            ["sh", str(self.package / "install.sh"), str(self.prefix)],
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_install_and_forward_arguments(self):
        self.mock_host()
        (self.package / "ARCHITECTURE").write_text("x86_64\n")
        self.prefix.joinpath("bin").mkdir(parents=True, exist_ok=True)
        original = self.prefix / "bin/codex"
        original.write_text("existing official CLI")
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run(
            [
                str(self.prefix / "bin/codex-suggest"),
                "resume",
                "a prompt with spaces",
                "--model",
                "example",
            ],
            env=self.env,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(
            result.stdout.splitlines(),
            [
                "off",
                "--no-daemon",
                "-c",
                "tui.prompt_suggestions=true",
                "resume",
                "a prompt with spaces",
                "--model",
                "example",
            ],
        )
        self.assertEqual(original.read_text(), "existing official CLI")
        self.assertTrue(
            (
                self.prefix
                / "share/codex-prompt-suggestions/codex-resources/zsh/bin/zsh"
            ).is_file()
        )

    def test_incompatible_hosts_are_rejected_before_installation(self):
        for system, arch, libc in (
            ("Darwin", "x86_64", "2.39"),
            ("Linux", "aarch64", "2.39"),
            ("Linux", "x86_64", "2.35"),
        ):
            with self.subTest(system=system, arch=arch, libc=libc):
                self.mock_host(system, arch, libc)
                self.assertNotEqual(self.install().returncode, 0)
                self.assertFalse(self.prefix.exists())

    def test_missing_helper_is_rejected_before_installation(self):
        (self.package / "codex-resources/bwrap").unlink()
        self.assertNotEqual(self.install().returncode, 0)
        self.assertFalse(self.prefix.exists())

    def test_explicit_logging_preference_is_preserved(self):
        self.env["RUST_LOG"] = "debug"
        self.assertEqual(self.install().returncode, 0)
        result = subprocess.run(
            [str(self.prefix / "bin/codex-suggest"), "--version"],
            env=self.env,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(result.stdout.splitlines()[0], "debug")

    def test_missing_metadata_is_rejected_before_installation(self):
        (self.package / "codex-package.json").unlink()
        self.assertNotEqual(self.install().returncode, 0)
        self.assertFalse(self.prefix.exists())


if __name__ == "__main__":
    unittest.main()
