"""Exercise Linux package assembly before compiling the full CLI."""

import hashlib
import os
import platform
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(
    platform.system() == "Linux" and platform.machine() == "x86_64",
    "requires Linux x86_64 build tools",
)
class NativePackageTest(unittest.TestCase):
    def test_package_extract_and_install_static_executables(self):
        with tempfile.TemporaryDirectory(prefix="codex package test ") as temporary:
            root = Path(temporary)
            binaries = root / "binaries"
            binaries.mkdir()
            source = root / "fixture.c"
            source.write_text("int main(void) { return 0; }\n")
            for name in ("codex", "codex-code-mode-host", "bwrap"):
                subprocess.run(
                    ["cc", "-static", str(source), "-o", str(binaries / name)],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            digest = hashlib.sha256((binaries / "bwrap").read_bytes()).hexdigest()
            result = subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "scripts/linux/package-codex-suggest.sh"),
                    str(binaries),
                    str(root / "dist"),
                ],
                cwd=REPO_ROOT,
                env={**os.environ, "CODEX_BWRAP_SHA256": digest},
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
