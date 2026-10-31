import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
RUNNER = PROJECT / "chain.py"


class ChainCliTests(unittest.TestCase):
    def run_pipeline(self, directory, steps):
        pipeline = directory / "pipeline.json"
        pipeline.write_text(json.dumps({"steps": steps}), encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(RUNNER), "run", str(pipeline)],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_runs_steps_in_order_with_arguments(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            first = directory / "first.py"
            second = directory / "second.py"
            first.write_text(
                "from pathlib import Path\nPath('order.txt').write_text('first')\n",
                encoding="utf-8",
            )
            second.write_text(
                "import sys\nfrom pathlib import Path\n"
                "Path('order.txt').write_text(Path('order.txt').read_text() + sys.argv[1])\n",
                encoding="utf-8",
            )

            result = self.run_pipeline(
                directory,
                [
                    {"command": [sys.executable, str(first)]},
                    {"name": "append", "command": [sys.executable, str(second), " second"]},
                ],
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((directory / "order.txt").read_text(encoding="utf-8"), "first second")

    def test_stops_after_failure_and_reports_step(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            marker = directory / "should-not-exist"
            result = self.run_pipeline(
                directory,
                [
                    {"name": "intentional failure", "command": [sys.executable, "-c", "raise SystemExit(7)"]},
                    {
                        "command": [
                            sys.executable,
                            "-c",
                            f"from pathlib import Path; Path({str(marker)!r}).touch()",
                        ]
                    },
                ],
            )

            self.assertEqual(result.returncode, 7)
            self.assertIn("intentional failure exited with status 7", result.stderr)
            self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
