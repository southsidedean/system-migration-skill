#!/usr/bin/env python3
"""Tests for the migration scripts, using known answers and awkward file names.

  python3 scripts/test_scripts.py
"""
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable


def run(script, *args):
    return subprocess.run([PY, os.path.join(HERE, script)] + list(args),
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
        os.makedirs(self.src)
        os.makedirs(self.dst)

    def tearDown(self):
        for current, dirs, _files in os.walk(self.tmp):
            for name in dirs:
                os.chmod(os.path.join(current, name), 0o755)
        shutil.rmtree(self.tmp)

    def inventory(self, root, name):
        out = os.path.join(self.tmp, name)
        result = run("inventory.py", "--root", "home=" + root, "--output", out)
        self.assertEqual(result.returncode, 0, result.stderr)
        return out

    def compare(self):
        out = os.path.join(self.tmp, "cmp")
        result = run("compare.py", "--source", self.inventory(self.src, "s.tsv"),
                     "--dest", self.inventory(self.dst, "d.tsv"), "--output", out)
        with open(os.path.join(out, "summary.json")) as handle:
            return result, json.load(handle), out


class InventoryTests(Base):
    def test_awkward_names_are_all_recorded(self):
        names = ["a b.txt", "#hash.txt", "tab\there.txt", "new\nline.txt", "uni³.txt",
                 "semi;colon.txt", "per%cent.txt", "-dash.txt"]
        for name in names:
            write(self.src, name)
        out = self.inventory(self.src, "s.tsv")
        with open(out) as handle:
            rows = [line for line in handle if line.startswith("f\t")]
        self.assertEqual(len(rows), len(names))

    def test_finishes_with_end_marker_and_counts(self):
        write(self.src, "one.txt")
        out = self.inventory(self.src, "s.tsv")
        with open(out) as handle:
            last = handle.read().strip().splitlines()[-1]
        self.assertTrue(last.startswith("#END\t"))
        self.assertEqual(json.loads(last.split("\t", 1)[1])["files"], 1)

    def test_symlinks_are_not_followed(self):
        write(self.src, "real/file.txt")
        os.symlink(os.path.join(self.src, "real"), os.path.join(self.src, "link"))
        out = self.inventory(self.src, "s.tsv")
        with open(out) as handle:
            text = handle.read()
        self.assertEqual(sum(1 for line in text.splitlines() if line.startswith("f\t")), 1)
        self.assertEqual(sum(1 for line in text.splitlines() if line.startswith("l\t")), 1)

    def test_excluded_cache_is_counted(self):
        write(self.src, ".cache/x/y.bin")
        write(self.src, "keep.txt")
        out = self.inventory(self.src, "s.tsv")
        with open(out) as handle:
            rows = handle.read().splitlines()
        excluded = [r for r in rows if r.startswith("x\t")]
        self.assertEqual(len(excluded), 1)
        self.assertEqual(excluded[0].split("\t")[5], "1")

    def test_credential_store_is_counted_not_hashed(self):
        write(self.src, "Library/Keychains/login.keychain-db")
        out = self.inventory(self.src, "s.tsv")
        with open(out) as handle:
            rows = handle.read().splitlines()
        self.assertTrue(any(r.startswith("x\t") and "Keychains" in r for r in rows))
        self.assertFalse(any(r.startswith("f\t") and "login.keychain" in r for r in rows))

    @unittest.skipIf(os.geteuid() == 0, "root can read anything")
    def test_unreadable_is_recorded_not_skipped(self):
        write(self.src, "locked/secret.txt")
        os.chmod(os.path.join(self.src, "locked"), 0)
        out = self.inventory(self.src, "s.tsv")
        with open(out) as handle:
            self.assertIn("err:EACCES", handle.read())

    def test_missing_root_fails(self):
        result = run("inventory.py", "--root", "home=/no/such/place", "--output", os.path.join(self.tmp, "x"))
        self.assertNotEqual(result.returncode, 0)


class CompareTests(Base):
    def test_every_class_with_known_answers(self):
        write(self.src, "same.txt", b"same " * 30)
        write(self.dst, "same.txt", b"same " * 30)
        write(self.src, "changed.txt", b"before " * 30)
        write(self.dst, "changed.txt", b"after " * 30)
        write(self.src, "gone.txt", b"gone " * 30)
        write(self.src, "old/place.txt", b"moved " * 30)
        write(self.dst, "new/place.txt", b"moved " * 30)
        write(self.src, "thing", b"file " * 30)
        write(self.dst, "thing/inside.txt", b"inside " * 30)
        write(self.dst, "extra.txt", b"extra " * 30)
        result, summary, _ = self.compare()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(summary["classes"], {
            "identical": 1, "different": 1, "missing": 1, "moved": 1,
            "type-mismatch": 1, "blocked": 0, "unverified": 0})
        self.assertEqual(summary["source_files"], summary["classified"])
        self.assertEqual(summary["dest_only_files"], 3)

    def test_folder_that_arrived_empty_is_caught(self):
        write(self.src, "folder/a.txt", b"a " * 50)
        write(self.src, "folder/sub/b.txt", b"b " * 50)
        os.makedirs(os.path.join(self.dst, "folder"))
        result, summary, _ = self.compare()
        self.assertEqual(summary["empty_dirs_at_dest"], ["home/folder"])
        self.assertIn("EMPTY AT DESTINATION", result.stdout)

    def test_tiny_coincidental_match_is_not_called_moved(self):
        write(self.src, "a/tiny.txt", b"x")
        write(self.dst, "b/other.txt", b"x")
        _, summary, _ = self.compare()
        self.assertEqual(summary["classes"]["missing"], 1)
        self.assertEqual(summary["classes"]["moved"], 0)

    @unittest.skipIf(os.geteuid() == 0, "root can read anything")
    def test_blocked_destination_is_not_called_missing(self):
        write(self.src, "locked/file.txt")
        write(self.dst, "locked/file.txt")
        os.chmod(os.path.join(self.dst, "locked"), 0)
        _, summary, _ = self.compare()
        self.assertEqual(summary["classes"]["blocked"], 1)
        self.assertEqual(summary["classes"]["missing"], 0)

    def test_partial_inventory_is_refused(self):
        write(self.src, "a.txt")
        good = self.inventory(self.src, "s.tsv")
        with open(good) as handle:
            lines = handle.read().splitlines()
        broken = os.path.join(self.tmp, "broken.tsv")
        with open(broken, "w") as handle:
            handle.write("\n".join(lines[:-1]) + "\n")
        result = run("compare.py", "--source", broken, "--dest", good, "--output", os.path.join(self.tmp, "o"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("didn't finish", result.stderr)

    def test_truncated_inventory_is_refused(self):
        write(self.src, "a.txt")
        write(self.src, "b.txt", b"b " * 40)
        good = self.inventory(self.src, "s.tsv")
        with open(good) as handle:
            lines = handle.read().splitlines()
        dropped = [line for line in lines if not (line.startswith("f\t") and "a.txt" in line)]
        broken = os.path.join(self.tmp, "broken.tsv")
        with open(broken, "w") as handle:
            handle.write("\n".join(dropped) + "\n")
        result = run("compare.py", "--source", broken, "--dest", good, "--output", os.path.join(self.tmp, "o"))
        self.assertNotEqual(result.returncode, 0)

    def test_empty_source_fails_rather_than_looking_clean(self):
        result, summary, _ = self.compare()
        self.assertEqual(summary["source_files"], 0)
        self.assertEqual(result.returncode, 2)

    def test_conflicts_between_sources(self):
        other = os.path.join(self.tmp, "other")
        write(self.src, "same.txt", b"same " * 20)
        write(other, "same.txt", b"same " * 20)
        write(self.src, "clash.txt", b"one " * 20)
        write(other, "clash.txt", b"two " * 20)
        write(self.src, "single.txt", b"single " * 20)
        out = os.path.join(self.tmp, "conflicts")
        result = run("compare.py", "--conflicts", self.inventory(self.src, "a.tsv"),
                     self.inventory(other, "b.tsv"), "--output", out)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {
            "paths": 3, "conflicts": 1, "same_everywhere": 1, "one_source_only": 1})
        with open(os.path.join(out, "conflicts.tsv")) as handle:
            self.assertIn("clash.txt", handle.read())


class ScanTests(Base):
    PLANTED_SECRET = "plantedvalue1234567890"

    def scan(self, *terms):
        path = os.path.join(self.tmp, "terms.txt")
        with open(path, "w") as handle:
            handle.write("\n".join(terms) + "\n")
        out = os.path.join(self.tmp, "scan.tsv")
        result = run("scan_sensitive.py", "--root", self.src, "--terms", path, "--output", out)
        with open(out) as handle:
            return result, handle.read()

    def test_innocent_name_with_matching_contents_is_found(self):
        write(self.src, "Insurance/records.yaml", b"gateway for ExampleCustomer prod\nExampleCustomer again\n")
        result, text = self.scan("examplecustomer")
        self.assertEqual(result.returncode, 0, result.stderr)
        row = [line for line in text.splitlines() if line.startswith("match\tcontent")]
        self.assertEqual(len(row), 1)
        self.assertEqual(row[0].split("\t")[3], "2")

    def test_output_never_contains_the_matching_text(self):
        write(self.src, "notes.txt", ("examplecustomer token=%s\n" % self.PLANTED_SECRET).encode())
        result, text = self.scan("examplecustomer")
        self.assertNotIn(self.PLANTED_SECRET, text)
        self.assertNotIn(self.PLANTED_SECRET, result.stdout + result.stderr)
        self.assertNotIn("token=", text)

    def test_name_match_and_archive_member_name(self):
        write(self.src, "examplecustomer-logs/x.log", b"nothing")
        archive = os.path.join(self.src, "bundle.tar")
        inner = os.path.join(self.tmp, "examplecustomer.txt")
        with open(inner, "w") as handle:
            handle.write("x")
        subprocess.run(["tar", "-cf", archive, "-C", self.tmp, "examplecustomer.txt"], check=True)
        _, text = self.scan("examplecustomer")
        self.assertIn("match\tname\texamplecustomer", text)
        self.assertIn("match\tarchive-member-name\texamplecustomer", text)
        self.assertIn("archive-contents-not-searched", text)

    def test_unreadable_formats_are_reported_not_clean(self):
        write(self.src, "report.pdf", b"%PDF examplecustomer")
        write(self.src, "blob.bin", b"\0\0\0binary examplecustomer")
        _, text = self.scan("examplecustomer")
        self.assertIn("not-searched\tformat", text)
        self.assertIn("not-searched\tbinary", text)
        self.assertNotIn("match\tcontent", text)

    def test_secrets_flagged_by_name_and_content(self):
        write(self.src, "app/.env", b"X=1\n")
        write(self.src, "notes.txt", b"-----BEGIN OPENSSH PRIVATE KEY-----\n")
        _, text = self.scan("unused-term")
        self.assertIn("builtin:secret-filename", text)
        self.assertIn("builtin:private-key", text)

    def test_credential_stores_are_never_read(self):
        for store in ("Library/Keychains", ".gnupg", ".local/share/keyrings"):
            write(self.src, store + "/login.db", b"examplecustomer")
        write(self.src, "plain.txt", b"examplecustomer")
        _, text = self.scan("examplecustomer")
        self.assertEqual(text.count("match\tcontent"), 1)
        self.assertEqual(text.count("not-searched\tcredential-store"), 3)

    def test_empty_terms_refused(self):
        path = os.path.join(self.tmp, "terms.txt")
        with open(path, "w") as handle:
            handle.write("\n# only a comment\n")
        result = run("scan_sensitive.py", "--root", self.src, "--terms", path,
                     "--output", os.path.join(self.tmp, "o"))
        self.assertNotEqual(result.returncode, 0)

    def test_no_files_is_a_failure_not_a_clean_scan(self):
        result, _ = self.scan("anything")
        self.assertEqual(result.returncode, 2)


class AwakeTests(unittest.TestCase):
    def test_passes_exit_status_and_leaves_nothing(self):
        script = os.path.join(HERE, "run-awake.sh")
        self.assertTrue(os.stat(script).st_mode & stat.S_IXUSR, "run-awake.sh must be executable")
        self.assertEqual(subprocess.run([script, "sh", "-c", "exit 7"], capture_output=True).returncode, 7)
        self.assertEqual(subprocess.run([script], capture_output=True).returncode, 64)


if __name__ == "__main__":
    unittest.main()
