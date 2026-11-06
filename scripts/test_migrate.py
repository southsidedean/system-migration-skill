#!/usr/bin/env python3
"""Tests for migrate.py, using known answers and planted traps.

  python3 scripts/test_migrate.py
"""
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
OK, FAILED, BAD = 0, 1, 2


def migrate(*args):
    return subprocess.run([sys.executable, os.path.join(HERE, "migrate.py")] + list(args),
                          capture_output=True, text=True)


def write(root, rel, data=b"data " * 20):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(data)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.src = os.path.join(self.tmp, "src")
        self.dst = os.path.join(self.tmp, "dst")
        self.dir = os.path.join(self.tmp, "migration")
        os.makedirs(self.src)
        os.makedirs(self.dst)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def plan(self, plan_file="plan.json", **fields):
        fields.setdefault("approved_by_user", True)
        path = os.path.join(self.tmp, plan_file)
        with open(path, "w") as handle:
            json.dump(fields, handle)
        return path

    def init(self):
        self.assertEqual(migrate("init", "--dir", self.dir, "--shape", "one-to-one",
                                 "--source", "old", "--dest", "new").returncode, OK)


class CopyTests(Base):
    def copy_plan(self, items, **extra):
        return self.plan(source=self.src, dest=self.dst, items=items, **extra)

    def test_listed_folder_arrives_with_its_contents(self):
        write(self.src, "folder/sub/deep.txt")
        write(self.src, "plain.txt")
        result = migrate("copy", "--plan", self.copy_plan(["folder", "plain.txt"]), "--run")
        self.assertEqual(result.returncode, OK, result.stdout + result.stderr)
        self.assertTrue(os.path.exists(os.path.join(self.dst, "folder/sub/deep.txt")))
        self.assertIn("missing=0", result.stdout)

    def test_hash_prefixed_name_is_not_dropped(self):
        write(self.src, "#hash name.txt")
        result = migrate("copy", "--plan", self.copy_plan(["#hash name.txt"]), "--run")
        self.assertEqual(result.returncode, OK, result.stdout + result.stderr)
        self.assertTrue(os.path.exists(os.path.join(self.dst, "#hash name.txt")))

    def test_newer_destination_file_is_kept_and_reported(self):
        write(self.src, "a.txt", b"from source")
        write(self.dst, "a.txt", b"newer destination")
        result = migrate("copy", "--plan", self.copy_plan(["a.txt"]), "--run")
        self.assertEqual(result.returncode, FAILED)
        self.assertIn("different=1", result.stdout)
        with open(os.path.join(self.dst, "a.txt"), "rb") as handle:
            self.assertEqual(handle.read(), b"newer destination")

    def test_missing_source_fails_rather_than_looking_clean(self):
        result = migrate("copy", "--plan", self.copy_plan(["nope"]), "--run")
        self.assertEqual(result.returncode, FAILED)

    def test_dry_run_writes_nothing(self):
        write(self.src, "a.txt")
        result = migrate("copy", "--plan", self.copy_plan(["a.txt"]))
        self.assertEqual(result.returncode, OK, result.stderr)
        self.assertIn("DRY RUN", result.stdout)
        self.assertFalse(os.path.exists(os.path.join(self.dst, "a.txt")))

    def test_run_refuses_unapproved_plan(self):
        write(self.src, "a.txt")
        result = migrate("copy", "--plan", self.copy_plan(["a.txt"], approved_by_user=False), "--run")
        self.assertNotEqual(result.returncode, OK)
        self.assertFalse(os.path.exists(os.path.join(self.dst, "a.txt")))

    def test_escaping_paths_are_refused(self):
        for bad in ("../outside", "/etc/passwd", ".", "a/../.."):
            result = migrate("copy", "--plan", self.copy_plan([bad]), "--run")
            self.assertNotEqual(result.returncode, OK, bad)


@unittest.skipUnless(os.environ.get("MIGRATE_TEST_HOST"), "set MIGRATE_TEST_HOST=user@host to test over SSH")
class RemoteTests(Base):
    """The host must accept SSH keys and be able to read this temporary folder."""

    def remote(self, path):
        return "%s:%s" % (os.environ["MIGRATE_TEST_HOST"], path)

    def test_copy_over_ssh_with_awkward_names(self):
        names = ["#hash name.txt", "a b/c d.txt", "uni³.txt", "semi;colon.txt", "plain.txt", "paren(1).txt"]
        for name in names:
            write(self.src, name)
        plan = self.plan(source=self.remote(self.src), dest=self.dst, items=["#hash name.txt", "a b", "uni³.txt", "semi;colon.txt", "plain.txt", "paren(1).txt"])
        result = migrate("copy", "--plan", plan, "--run")
        self.assertEqual(result.returncode, OK, result.stdout + result.stderr)
        for name in names:
            self.assertTrue(os.path.exists(os.path.join(self.dst, name)), name)

    def test_archive_over_ssh(self):
        write(self.src, "work/a b.txt")
        plan = self.plan("a.json", name="remote", source=self.remote(self.src), items=["work"], dest_dir=self.dst)
        result = migrate("archive", "--plan", plan)
        self.assertEqual(result.returncode, OK, result.stdout + result.stderr)

    def test_delete_over_ssh(self):
        write(self.src, "gone.txt")
        write(self.src, "keep.txt")
        plan = self.plan("d.json", base=self.remote(self.src), items=["gone.txt"])
        result = migrate("delete", "--plan", plan, "--run")
        self.assertEqual(result.returncode, OK, result.stdout + result.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.src, "gone.txt")))
        self.assertTrue(os.path.exists(os.path.join(self.src, "keep.txt")))


class DeleteTests(Base):
    def delete_plan(self, items, **extra):
        return self.plan("delete.json", base=self.src, items=items, **extra)

    def test_deletes_exact_paths_only(self):
        write(self.src, "list-a/one.txt")
        write(self.src, "list-a-similar/two.txt")
        result = migrate("delete", "--plan", self.delete_plan(["list-a"]), "--run")
        self.assertEqual(result.returncode, OK, result.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.src, "list-a")))
        self.assertTrue(os.path.exists(os.path.join(self.src, "list-a-similar/two.txt")))

    def test_wildcards_do_not_expand(self):
        write(self.src, "keep.txt")
        result = migrate("delete", "--plan", self.delete_plan(["*"]), "--run")
        self.assertEqual(result.returncode, FAILED)
        self.assertTrue(os.path.exists(os.path.join(self.src, "keep.txt")))

    def test_dry_run_by_default(self):
        write(self.src, "a.txt")
        result = migrate("delete", "--plan", self.delete_plan(["a.txt"]))
        self.assertIn("DRY RUN", result.stdout)
        self.assertTrue(os.path.exists(os.path.join(self.src, "a.txt")))

    def test_one_missing_path_stops_everything(self):
        write(self.src, "a.txt")
        result = migrate("delete", "--plan", self.delete_plan(["a.txt", "gone.txt"]), "--run")
        self.assertEqual(result.returncode, FAILED)
        self.assertTrue(os.path.exists(os.path.join(self.src, "a.txt")))

    def test_symlink_target_survives(self):
        write(self.tmp, "outside/keep.txt")
        os.symlink(os.path.join(self.tmp, "outside"), os.path.join(self.src, "link"))
        result = migrate("delete", "--plan", self.delete_plan(["link"]), "--run")
        self.assertEqual(result.returncode, OK, result.stderr)
        self.assertTrue(os.path.exists(os.path.join(self.tmp, "outside/keep.txt")))

    def test_archive_mismatch_blocks_deletion(self):
        write(self.src, "a.txt", b"original")
        archive = os.path.join(self.tmp, "a.tar.gz")
        with tarfile.open(archive, "w:gz") as handle:
            handle.add(os.path.join(self.src, "a.txt"), arcname="a.txt")
        write(self.src, "a.txt", b"changed after archiving")
        result = migrate("delete", "--plan", self.delete_plan(["a.txt"]), "--run", "--verify-archive", archive)
        self.assertEqual(result.returncode, FAILED)
        self.assertTrue(os.path.exists(os.path.join(self.src, "a.txt")))


class ArchiveTests(Base):
    def archive_plan(self, items=("work",)):
        return self.plan("archive.json", name="employer", source=self.src, items=list(items), dest_dir=self.dst)

    def test_builds_and_verifies(self):
        write(self.src, "work/a b.txt")
        write(self.src, "work/sub/c.txt", b"c " * 50)
        result = migrate("archive", "--plan", self.archive_plan())
        self.assertEqual(result.returncode, OK, result.stdout + result.stderr)
        self.assertIn("verified_files=2", result.stdout)
        for suffix in (".tar.gz", ".tar.gz.sha256", ".filelist.txt", ".manifest.json"):
            self.assertTrue(os.path.exists(os.path.join(self.dst, "employer" + suffix)), suffix)
        self.assertFalse(os.path.exists(os.path.join(self.dst, "employer.tar.gz.partial")))
        tool = ["shasum", "-a", "256"] if shutil.which("shasum") else ["sha256sum"]
        check = subprocess.run(tool + ["-c", "employer.tar.gz.sha256"], cwd=self.dst, capture_output=True)
        self.assertEqual(check.returncode, 0)

    def test_symlink_pointing_outside_is_flagged(self):
        write(self.src, "elsewhere/SKILL.md")
        write(self.src, "work/a.txt")
        os.symlink("../elsewhere/SKILL.md", os.path.join(self.src, "work/link"))
        result = migrate("archive", "--plan", self.archive_plan())
        self.assertIn("symlinks_outside=1", result.stdout)
        with open(os.path.join(self.dst, "employer.manifest.json")) as handle:
            self.assertEqual(json.load(handle)["symlinks_pointing_outside"][0][0], "work/link")

    def test_existing_archive_needs_replace_and_survives_failure(self):
        write(self.src, "work/a.txt")
        plan = self.archive_plan()
        self.assertEqual(migrate("archive", "--plan", plan).returncode, OK)
        path = os.path.join(self.dst, "employer.tar.gz")
        with open(path, "rb") as handle:
            before = handle.read()
        self.assertNotEqual(migrate("archive", "--plan", plan).returncode, OK)
        os.unlink(os.path.join(self.src, "work/a.txt"))
        write(self.src, "work/b.txt")
        result = migrate("archive", "--plan", plan, "--replace")
        self.assertEqual(result.returncode, FAILED)
        self.assertIn("would be lost", result.stderr)
        with open(path, "rb") as handle:
            self.assertEqual(handle.read(), before)
        self.assertFalse(os.path.exists(path + ".partial"))


class StateAndGateTests(Base):
    def record(self, kind, status="pass", *extra):
        return migrate("record", "--dir", self.dir, "--source", "old", "--kind", kind, "--status", status, *extra)

    def compare_summary(self, **classes):
        path = os.path.join(self.tmp, "summary.json")
        with open(path, "w") as handle:
            json.dump({"classes": dict({"identical": 5, "missing": 0}, **classes), "empty_dirs_at_dest": []}, handle)
        return path

    def pass_all(self):
        self.record("final-compare", "pass", "--file", self.compare_summary())
        for kind in ("final-backup", "credentials-retested", "secrets-reviewed", "git-clean",
                     "local-app-data-checked", "archives-verified", "licenses-and-accounts"):
            self.record(kind)

    def gate(self, *extra):
        return migrate("gate", "--dir", self.dir, "--source", "old", *extra)

    def test_no_evidence_fails(self):
        self.init()
        result = self.gate()
        self.assertEqual(result.returncode, FAILED)
        self.assertIn("GATE FAILED", result.stdout)

    def test_all_evidence_passes(self):
        self.init()
        self.pass_all()
        self.assertEqual(self.gate().returncode, OK)

    def test_source_change_makes_evidence_stale(self):
        self.init()
        self.pass_all()
        result = self.gate("--source-changed", "2999-01-01T00:00:00+00:00")
        self.assertEqual(result.returncode, FAILED)
        self.assertIn("stale", result.stdout)

    def test_old_evidence_is_stale(self):
        self.init()
        self.pass_all()
        path = os.path.join(self.dir, "state.json")
        with open(path) as handle:
            state = json.load(handle)
        for entry in state["evidence"]:
            entry["date"] = "2000-01-01T00:00:00+00:00"
        with open(path, "w") as handle:
            json.dump(state, handle)
        self.assertEqual(self.gate().returncode, FAILED)

    def test_missing_files_fail_the_compare_check(self):
        self.init()
        self.pass_all()
        self.record("final-compare", "pass", "--file", self.compare_summary(missing=3))
        self.assertEqual(self.gate().returncode, FAILED)

    def test_accepted_risk_needs_a_note_and_then_passes(self):
        self.init()
        self.pass_all()
        self.assertNotEqual(self.record("git-clean", "accepted-risk").returncode, OK)
        self.assertEqual(self.record("git-clean", "accepted-risk", "--note", "user keeps the changes").returncode, OK)
        result = self.gate()
        self.assertEqual(result.returncode, OK)
        self.assertIn("ACCEPTED", result.stdout)

    def test_unknown_source_refused(self):
        self.init()
        self.assertNotEqual(migrate("gate", "--dir", self.dir, "--source", "other").returncode, OK)

    def test_status_is_short_and_points_to_next_step(self):
        self.init()
        result = migrate("status", "--dir", self.dir)
        self.assertEqual(result.returncode, OK)
        self.assertIn("phase=1", result.stdout)
        self.assertLess(len(result.stdout.splitlines()), 5)

    def test_decide_validates_and_renders(self):
        self.init()
        bad = migrate("decide", "--dir", self.dir, "--source", "old", "--item", "x", "--owner", "nobody",
                      "--secret", "no", "--action", "keep")
        self.assertNotEqual(bad.returncode, OK)
        good = migrate("decide", "--dir", self.dir, "--source", "old", "--item", "Old|Work", "--owner", "employer",
                       "--secret", "no", "--action", "archive", "--reason", "keep a copy")
        self.assertEqual(good.returncode, OK, good.stderr)
        with open(os.path.join(self.dir, "decisions.md")) as handle:
            text = handle.read()
        self.assertIn("Old\\|Work", text)
        self.assertIn("D1", text)

    def test_init_refuses_a_folder_that_is_in_use(self):
        write(self.dir, "someone-elses-plan.json", b"{}")
        result = migrate("init", "--dir", self.dir, "--shape", "absorb", "--source", "a", "--dest", "b")
        self.assertNotEqual(result.returncode, OK)
        self.assertFalse(os.path.exists(os.path.join(self.dir, "state.json")))

    def test_init_refuses_to_overwrite(self):
        self.init()
        self.assertNotEqual(migrate("init", "--dir", self.dir, "--shape", "absorb", "--source", "a", "--dest", "b").returncode, OK)


class CollectTests(Base):
    def test_writes_json_and_reports_counts(self):
        out = os.path.join(self.tmp, "collect.json")
        result = migrate("collect", "--output", out, "--timeout", "20")
        self.assertEqual(result.returncode, OK, result.stderr)
        with open(out) as handle:
            data = json.load(handle)
        self.assertIn("results", data)
        self.assertLess(len(result.stdout.splitlines()), 4)


class PassthroughTests(Base):
    def test_inventory_and_compare_through_entry_point(self):
        write(self.src, "a.txt")
        out = os.path.join(self.tmp, "s.tsv")
        self.assertEqual(migrate("inventory", "--root", "home=" + self.src, "--output", out).returncode, OK)
        result = migrate("compare", "--source", out, "--dest", out, "--output", os.path.join(self.tmp, "c"))
        self.assertEqual(result.returncode, OK, result.stderr)


if __name__ == "__main__":
    unittest.main()
