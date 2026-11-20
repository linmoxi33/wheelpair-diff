import json
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "bin", "wheelpair-diff")
IN = os.path.join(ROOT, "examples", "in")
A = os.path.join(IN, "demo_lib-1.0.0-py3-none-any.whl")
B = os.path.join(IN, "demo_lib-2.0.0-py3-none-any.whl")


def run(*args, **kw):
    return subprocess.run([sys.executable, BIN] + list(args), capture_output=True,
                          text=True, timeout=kw.get("timeout", 120))


class TestDiff(unittest.TestCase):
    def test_json_is_parseable(self):
        p = run("diff", A, B, "--json")
        self.assertEqual(p.returncode, 1)
        data = json.loads(p.stdout)
        self.assertEqual(data["summary"]["drifts"], 3)

    def test_exit_code_zero_when_identical(self):
        p = run("diff", A, A, "--json")
        self.assertEqual(p.returncode, 0)
        self.assertEqual(json.loads(p.stdout)["summary"]["drifts"], 0)

    def test_exit_code_one_on_drift(self):
        self.assertEqual(run("diff", A, B).returncode, 1)

    def test_exit_code_two_missing_file(self):
        p = run("diff", A, os.path.join(IN, "nope.whl"))
        self.assertEqual(p.returncode, 2)
        self.assertIn("no such file", p.stderr)

    def test_exit_code_two_not_a_wheel(self):
        junk = os.path.join(ROOT, "tests", "_junk.whl")
        with open(junk, "w") as fh:
            fh.write("not a zip")
        try:
            p = run("diff", junk, B)
            self.assertEqual(p.returncode, 2)
            self.assertIn("not a readable wheel", p.stderr)
        finally:
            os.remove(junk)

    def test_exit_code_two_on_bad_usage(self):
        self.assertEqual(run("diff").returncode, 2)

    def test_symbol_removed_is_reported(self):
        data = json.loads(run("diff", A, B, "--json").stdout)
        removed = [d for d in data["drifts"] if d["kind"] == "symbol_removed"]
        self.assertEqual([d["symbol"] for d in removed], ["demo_lib.helper"])
        self.assertEqual(removed[0]["severity"], "error")

    def test_outcome_kind_drift_is_reported(self):
        data = json.loads(run("diff", A, B, "--json").stdout)
        kinds = [d for d in data["drifts"] if d["kind"] == "outcome_kind"]
        self.assertTrue(kinds)
        first = kinds[0]
        self.assertEqual(first["a"]["kind"], "ok")
        self.assertEqual(first["b"]["type"], "ValueError")

    def test_every_drift_has_a_minimal_repro(self):
        data = json.loads(run("diff", A, B, "--json").stdout)
        for d in data["drifts"]:
            self.assertIn("python3 -c", d["minimal_repro"])
            self.assertIn(d["symbol"].rsplit(".", 1)[1], d["minimal_repro"])

    def test_versions_are_read_from_metadata(self):
        data = json.loads(run("diff", A, B, "--json").stdout)
        self.assertEqual(data["a"]["version"], "1.0.0")
        self.assertEqual(data["b"]["version"], "2.0.0")

    def test_summary_counts_match_records(self):
        data = json.loads(run("diff", A, B, "--json").stdout)
        s = data["summary"]
        self.assertEqual(s["by_severity"].get("error", 0) + s["by_severity"].get("warning", 0),
                         s["drifts"])
        self.assertGreaterEqual(s["calls_a"], 4)
        self.assertGreaterEqual(s["calls_b"], 4)

    def test_output_is_deterministic(self):
        one = json.loads(run("diff", A, B, "--json").stdout)["summary"]
        two = json.loads(run("diff", A, B, "--json").stdout)["summary"]
        self.assertEqual(one, two)

    def test_probe_subcommand(self):
        p = run("probe", A, "--json")
        self.assertEqual(p.returncode, 0)
        data = json.loads(p.stdout)
        self.assertEqual(data["version"], "1.0.0")
        self.assertGreater(len(data["records"]), 0)

    def test_human_output_mentions_both_wheels(self):
        p = run("diff", A, B)
        self.assertIn("demo_lib-1.0.0", p.stdout)
        self.assertIn("demo_lib-2.0.0", p.stdout)
        self.assertIn("drift: 3", p.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
