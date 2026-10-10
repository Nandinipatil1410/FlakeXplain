"""Guard the complete build tooling for the pinned SunPy and ASDF sources."""
import json
from pathlib import Path
import unittest


class SunpySetupTests(unittest.TestCase):
    def test_asdf_version_tooling_is_bootstrapped_before_snapshot_install(self):
        root = Path(__file__).resolve().parents[1]
        config = json.loads((root / "cannier-replication/remaining-configs.json")
                            .read_text(encoding="utf-8"))["sunpy"]
        self.assertEqual(config["installer"], "cannier_snapshot")
        self.assertIn("setuptools-scm==5.0.2", config["bootstrap_pkgs"])
        snapshot = (root / config["snapshot_path"]).read_text(encoding="utf-8")
        self.assertIn("asdf==2.8.1", snapshot.splitlines())

    def test_sunpy_build_requirements_are_supplied_without_isolation(self):
        root = Path(__file__).resolve().parents[1]
        config = json.loads((root / "cannier-replication/remaining-configs.json")
                            .read_text(encoding="utf-8"))["sunpy"]
        bootstrap = config["bootstrap_pkgs"]
        # The pinned pyproject.toml requires these four build distributions.
        for requirement in ("setuptools==57.5.0", "setuptools-scm==5.0.2",
                            "wheel==0.37.1", "extension-helpers==0.1"):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, bootstrap)
        # oldest-supported-numpy is an isolated-build dependency selector.
        # With --no-build-isolation, build against the recorded runtime NumPy
        # installed by the snapshot step; do not let the selector downgrade it.
        snapshot = (root / config["snapshot_path"]).read_text(encoding="utf-8")
        self.assertIn("numpy==1.21.1", snapshot.splitlines())
        self.assertFalse(any(pin.startswith("oldest-supported-numpy")
                             for pin in bootstrap))


if __name__ == "__main__":
    unittest.main()
