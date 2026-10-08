"""Exercise native packaging tools before spending time compiling the full CLI."""

import platform
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(platform.system() == "Darwin", "requires native macOS tools")
class NativePackageTest(unittest.TestCase):
    def test_package_sign_extract_and_install_native_executables(self):
        arch = platform.machine()
        target = {"arm64": "aarch64-apple-darwin", "x86_64": "x86_64-apple-darwin"}[
            arch
        ]
        with tempfile.TemporaryDirectory(prefix="codex package test ") as temporary:
            root = Path(temporary)
            binaries = root / "binaries"
            binaries.mkdir()
            source = root / "fixture.c"
            source.write_text("int main(void) { return 0; }\n")
            for name in ("codex", "codex-code-mode-host"):
                subprocess.run(
                    ["cc", "-arch", arch, str(source), "-o", str(binaries / name)],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            result = subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "scripts/macos/package-codex-suggest.sh"),
                    target,
                    str(binaries),
                    str(root / "dist"),
                ],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Verified archive:", result.stdout)
            self.assertEqual(len(list((root / "dist").glob("*.tar.gz"))), 1)
            self.assertEqual(len(list((root / "dist").glob("*.sha256"))), 1)


if __name__ == "__main__":
    unittest.main()
