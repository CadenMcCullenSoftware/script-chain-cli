import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import chain

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

    def test_rejects_step_without_command(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            result = self.run_pipeline(Path(temporary_directory), [{"name": "missing command"}])

            self.assertEqual(result.returncode, 2)
            self.assertIn("step 1 needs a non-empty string list in 'command'", result.stderr)

    def run_repos(self, *arguments):
        return subprocess.run(
            [sys.executable, str(RUNNER), "repos", *arguments],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_lists_repository_catalog(self):
        result = self.run_repos("list")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CadenMcCullenSoftware/script-chain-cli", result.stdout)
        self.assertIn("19 repositories", result.stdout)

    def test_status_reports_missing_local_repositories(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            result = self.run_repos("status", "--root", temporary_directory)

        self.assertEqual(result.returncode, 1)
        self.assertIn("not found", result.stdout)

    def test_checks_only_display_test_command_without_run_flag(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo = Path(temporary_directory) / "script-chain-cli"
            (repo / "tests").mkdir(parents=True)
            (repo / "tests" / "test_sample.py").write_text(
                "import unittest\n", encoding="utf-8"
            )
            result = self.run_repos(
                "checks", "script-chain-cli", "--root", temporary_directory
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("not run; pass --run", result.stdout)

    def test_docs_lists_markdown_and_skips_build_directories(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo = Path(temporary_directory) / "script-chain-cli"
            (repo / "docs").mkdir(parents=True)
            (repo / "docs" / "guide.md").write_text("guide", encoding="utf-8")
            (repo / "build").mkdir()
            (repo / "build" / "generated.md").write_text("generated", encoding="utf-8")
            result = self.run_repos(
                "docs", "script-chain-cli", "--root", temporary_directory
            )
            read_result = self.run_repos(
                "read-doc",
                "script-chain-cli",
                "docs/guide.md",
                "--root",
                temporary_directory,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("docs/guide.md", result.stdout)
        self.assertNotIn("generated.md", result.stdout)
        self.assertEqual(read_result.returncode, 0, read_result.stderr)
        self.assertEqual(read_result.stdout, "guide\n")

    def test_add_and_remove_repository_in_user_config(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            config = Path(temporary_directory) / "config" / "repos.json"
            added = self.run_repos(
                "add",
                "example-org/example-repo",
                "--description",
                "Example",
                "--config",
                str(config),
            )
            listed = self.run_repos("list", "--config", str(config))
            removed = self.run_repos(
                "remove", "example-repo", "--config", str(config)
            )
            listed_after_remove = self.run_repos("list", "--config", str(config))

        self.assertEqual(added.returncode, 0, added.stderr)
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertIn("example-org/example-repo", listed.stdout)
        self.assertEqual(removed.returncode, 0, removed.stderr)
        self.assertNotIn("example-org/example-repo", listed_after_remove.stdout)

    def test_add_rejects_path_traversal_repository_names(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            config = Path(temporary_directory) / "config" / "repos.json"
            result = self.run_repos(
                "add", "example-org/..", "--config", str(config)
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("OWNER/REPOSITORY", result.stderr)
        self.assertFalse(config.exists())

    def test_read_doc_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo = Path(temporary_directory) / "script-chain-cli"
            repo.mkdir()
            outside = Path(temporary_directory) / "outside.md"
            outside.write_text("not in repo", encoding="utf-8")
            result = self.run_repos(
                "read-doc",
                "script-chain-cli",
                "../outside.md",
                "--root",
                temporary_directory,
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("must stay inside the repository", result.stderr)

    def test_checks_run_requires_explicit_repository_selection(self):
        result = self.run_repos("checks", "--run")

        self.assertEqual(result.returncode, 2)
        self.assertIn("specify repository names", result.stderr)

    @patch("chain.subprocess.run")
    def test_discovery_reads_github_metadata_without_mutation(self, run):
        run.return_value = subprocess.CompletedProcess(
            args=["gh"],
            returncode=0,
            stdout=json.dumps(
                [
                    {
                        "nameWithOwner": "example-org/example-repo",
                        "description": "Example project",
                        "primaryLanguage": {"name": "Python"},
                    }
                ]
            ),
            stderr="",
        )

        discovered = chain.discover_repositories("example-org")

        self.assertEqual(
            discovered,
            [
                {
                    "name": "example-org/example-repo",
                    "language": "Python",
                    "description": "Example project",
                }
            ],
        )
        self.assertEqual(run.call_args.args[0][:4], ["gh", "repo", "list", "example-org"])


if __name__ == "__main__":
    unittest.main()
