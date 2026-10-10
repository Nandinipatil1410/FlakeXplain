"""Guard the build tooling required by SunPy's historical ASDF dependency."""
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


if __name__ == "__main__":
    unittest.main()
