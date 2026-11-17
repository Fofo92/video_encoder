from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "copy_version_replacement", ROOT / "lib/video_encoder/copy_version_replacement.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CopyVersionReplacementTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.database = self.root / "queue.sqlite3"
        with self.db() as db:
            db.execute("CREATE TABLE jobs(id INTEGER PRIMARY KEY, project_path TEXT, output_path TEXT, status TEXT)")
        self.old = self.root / "Monstres gentils (Szelíd).json"
        self.source = self.old.with_suffix(".mkv")
        self.project = self.root / "Monstres gentils (Szelíd) - VOST.json"
        self.video = self.project.with_suffix(".mkv")
        self.old.write_bytes(MODULE.encoded({"format": "video_encoder.trim_project", "version": 2,
                                            "sources": [{"id": "capture", "path": "/commun/source.m2t"}]}))
        self.source.write_bytes(b"old VM source with french and original")
        self.video.write_bytes(b"new VOST with original audio")
        document = {"format": "video_encoder.copy_version", "version": 2, "project_id": "same-project",
                    "vidb": {"record_id": 42, "binding_token": "binding"},
                    "sources": [{"id": "copy", "path": str(self.source)}],
                    "version_change": {"profile": "VOST", "source_path": str(self.source),
                                       "identity": MODULE.signature(self.source), "audio_index": 2, "video_index": 0,
                                       "original_confirmed": True, "burned_french_confirmed": True}}
        self.project.write_bytes(MODULE.encoded(document))
        self.receipt = Path(str(self.video) + MODULE.SUFFIX)
        self.receipt.write_bytes(MODULE.encoded({
            "format": "video_encoder.completed_export", "version": 1, "project_path": str(self.project),
            "output_path": str(self.video), "project_id": "same-project", "roles": ["original"],
            "byte_size": self.video.stat().st_size,
            "modified_at": datetime.fromtimestamp(self.video.stat().st_mtime, timezone.utc).isoformat(),
            "project_sha256": MODULE.digest(self.project.read_bytes()), "version_change": document["version_change"],
            "vidb": document["vidb"], "probe": {"format": {"filename": str(self.video)}}}))
        # Match Ruby Time#iso8601(6), which truncates sub-microsecond digits.
        stamp = self.video.stat().st_mtime_ns
        dt = datetime.fromtimestamp(stamp // 1_000_000_000, timezone.utc).replace(
            microsecond=(stamp % 1_000_000_000) // 1000)
        receipt = json.loads(self.receipt.read_text())
        receipt["modified_at"] = dt.isoformat(timespec="microseconds")
        self.receipt.write_bytes(MODULE.encoded(receipt))
        with self.db() as db:
            db.execute("INSERT INTO jobs VALUES (1,?,?, 'done')", (str(self.old), str(self.source)))
            db.execute("INSERT INTO jobs VALUES (2,?,?, 'done')", (str(self.project), str(self.video)))

    def db(self):
        return sqlite3.connect(self.database)

    def replace(self, preview=False):
        return MODULE.replace(str(self.database), str(self.project), str(self.root),
                              self.old.stem, preview=preview)

    def jobs(self):
        with self.db() as db:
            return db.execute("SELECT id,project_path,output_path,status FROM jobs ORDER BY id").fetchall()

    def test_preview_shows_archival_and_replacement_without_changing_files_or_history(self):
        before = {p.name: p.read_bytes() for p in self.root.iterdir() if p.suffix != ".sqlite3"}
        jobs = self.jobs()
        plan = self.replace(preview=True)
        self.assertEqual(plan["project_path"], str(self.old))
        self.assertIn({"source": str(self.video), "destination": str(self.source)}, plan["files"])
        self.assertEqual(jobs, self.jobs())
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir() if p.suffix != ".sqlite3"})
        self.assertFalse((self.root / ".video_encoder_trash").exists())

    def test_replacement_archives_originals_retargets_jobs_and_never_creates_a_self_reference(self):
        original_project = self.old.read_bytes()
        original_video = self.source.read_bytes()
        converted_video = self.video.read_bytes()
        source_identity = MODULE.signature(self.source)
        self.assertEqual(self.replace(), str(self.old))
        self.assertEqual(self.source.read_bytes(), converted_video)
        document = json.loads(self.old.read_text())
        archived_source = Path(document["sources"][0]["path"])
        self.assertNotEqual(archived_source, self.source)
        self.assertEqual(archived_source.read_bytes(), original_video)
        self.assertEqual(MODULE.signature(archived_source), source_identity)
        self.assertEqual(document["version_change"]["source_path"], str(archived_source))
        jobs = self.jobs()
        self.assertEqual(Path(jobs[0][1]).read_bytes(), original_project)
        self.assertEqual(jobs[0][2], str(archived_source))
        self.assertEqual(jobs[1][1:3], (str(self.old), str(self.source)))
        receipt = json.loads(Path(str(self.source) + MODULE.SUFFIX).read_text())
        self.assertEqual(receipt["project_sha256"], MODULE.digest(self.old.read_bytes()))
        self.assertEqual(receipt["version_change"], document["version_change"])
        self.assertEqual(receipt["previous_output_path"], str(self.video))
        self.assertEqual(receipt["vidb"], document["vidb"])
        self.assertFalse(self.project.exists())
        self.assertFalse(self.video.exists())
        self.assertTrue((archived_source.parent / "manifest.json").is_file())
        with self.db() as db:
            self.assertEqual(db.execute("SELECT path FROM project_trash_roots").fetchone()[0],
                             str(archived_source.parent.parent))

    def test_missing_old_video_is_historical_and_is_not_replaced_by_a_reference_to_the_new_video(self):
        self.source.unlink()
        self.replace()
        document = json.loads(self.old.read_text())
        self.assertNotEqual(document["sources"][0]["path"], str(self.source))
        self.assertFalse(Path(document["sources"][0]["path"]).exists())
        receipt = json.loads(Path(str(self.source) + MODULE.SUFFIX).read_text())
        self.assertTrue(receipt["copy_version_replacement"]["source_missing_before_replacement"])

    def test_active_old_or_new_jobs_block_replacement(self):
        for job in (1, 2):
            for status in ("running", "queued", "deferred"):
                with self.db() as db:
                    db.execute("UPDATE jobs SET status=? WHERE id=?", (status, job))
                with self.assertRaises(ValueError):
                    self.replace()
                self.assertEqual(self.source.read_bytes(), b"old VM source with french and original")
                with self.db() as db:
                    db.execute("UPDATE jobs SET status='done'")

    def test_other_projects_using_the_source_are_not_silently_broken(self):
        other = self.root / "Other.json"
        other.write_bytes(MODULE.encoded({"version": 2, "sources": [{"path": str(self.source)}]}))
        with self.db() as db:
            db.execute("INSERT INTO jobs VALUES (3,?,?, 'queued')", (str(other), str(self.root / "other.mkv")))
        with self.assertRaisesRegex(ValueError, "autre préparation"):
            self.replace()
        self.assertTrue(self.project.exists())

    def old_export_receipt(self):
        stamp = self.source.stat().st_mtime_ns
        modified = datetime.fromtimestamp(stamp // 1_000_000_000, timezone.utc).replace(
            microsecond=stamp % 1_000_000_000 // 1000)
        receipt = {"format": "video_encoder.completed_export", "version": 1,
                   "project_path": str(self.old), "output_path": str(self.source),
                   "project_sha256": MODULE.digest(self.old.read_bytes()),
                   "byte_size": self.source.stat().st_size,
                   "modified_at": modified.isoformat(timespec="microseconds"),
                   "vidb": {"record_id": 42}}
        path = Path(str(self.source) + MODULE.SUFFIX)
        path.write_bytes(MODULE.encoded(receipt))
        return path

    def test_missing_old_json_can_be_replaced_using_the_verified_old_video_and_receipt(self):
        old_receipt = self.old_export_receipt()
        original_receipt = old_receipt.read_bytes()
        original_video = self.source.read_bytes()
        self.old.unlink()
        plan = self.replace(preview=True)
        self.assertFalse(self.old.exists())
        self.assertFalse((self.root / ".video_encoder_trash").exists())
        self.assertNotIn(str(self.old), [f["source"] for f in plan["files"]])
        self.replace()
        document = json.loads(self.old.read_text())
        archived = Path(document["sources"][0]["path"])
        self.assertNotEqual(archived, self.source)
        self.assertEqual(archived.read_bytes(), original_video)
        self.assertEqual(Path(str(archived) + MODULE.SUFFIX).read_bytes(), original_receipt)
        self.assertFalse(Path(self.jobs()[0][1]).exists())
        receipt = json.loads(old_receipt.read_text())
        self.assertTrue(receipt["copy_version_replacement"]["source_project_missing_before_replacement"])
        self.assertEqual(receipt["copy_version_replacement"]["source_project_sha256"],
                         json.loads(original_receipt)["project_sha256"])

    def test_missing_old_json_without_a_receipt_does_not_release_the_reserved_name(self):
        self.old.unlink()
        with self.assertRaisesRegex(ValueError, "vidéo initiale et son reçu"):
            self.replace()
        self.assertFalse((self.root / ".video_encoder_trash").exists())

    def test_missing_old_json_requires_a_receipt_for_the_same_record_and_video(self):
        path = self.old_export_receipt()
        original = json.loads(path.read_text())
        self.old.unlink()
        for field, value in [("vidb", {"record_id": 99}), ("byte_size", 123),
                             ("modified_at", "2000-01-01T00:00:00+00:00"), ("project_sha256", "invalid")]:
            path.write_bytes(MODULE.encoded(dict(original, **{field: value})))
            with self.assertRaises(ValueError):
                self.replace()
            self.assertTrue(self.video.exists())
            self.assertFalse(self.old.exists())

    def test_missing_old_json_and_video_cannot_be_replaced_from_only_a_receipt(self):
        self.old_export_receipt()
        self.old.unlink()
        self.source.unlink()
        with self.assertRaisesRegex(ValueError, "vidéo initiale et son reçu"):
            self.replace()

    def test_a_database_failure_with_missing_old_json_restores_files_without_inventing_a_project(self):
        old_receipt = self.old_export_receipt()
        self.old.unlink()
        paths = [self.source, self.project, self.video, self.receipt, old_receipt]
        before = {p: p.read_bytes() for p in paths}
        jobs = self.jobs()
        with self.db() as db:
            db.execute("CREATE TRIGGER refuse_update BEFORE UPDATE ON jobs "
                       "BEGIN SELECT RAISE(ABORT, 'queue failure'); END")
        with self.assertRaises(sqlite3.DatabaseError):
            self.replace()
        self.assertFalse(self.old.exists())
        self.assertEqual(before, {p: p.read_bytes() for p in paths})
        self.assertEqual(jobs, self.jobs())

    def test_different_source_or_changed_project_or_video_never_overwrites_any_file(self):
        original = self.source.read_bytes()
        self.source.write_bytes(b"different")
        with self.assertRaises(ValueError):
            self.replace()
        self.assertEqual(self.source.read_bytes(), b"different")
        self.source.write_bytes(original)
        self.project.write_bytes(self.project.read_bytes() + b" ")
        with self.assertRaises(ValueError):
            self.replace()
        self.assertTrue(self.video.exists())

    def test_a_database_failure_restores_old_files_new_files_and_job_paths(self):
        files = [self.old, self.source, self.project, self.video, self.receipt]
        before = {p: p.read_bytes() for p in files}
        jobs = self.jobs()
        with self.db() as db:
            db.execute("CREATE TRIGGER refuse_update BEFORE UPDATE ON jobs "
                       "BEGIN SELECT RAISE(ABORT, 'queue failure'); END")
        with self.assertRaises(sqlite3.DatabaseError):
            self.replace()
        self.assertEqual(before, {p: p.read_bytes() for p in files})
        self.assertEqual(jobs, self.jobs())
        self.assertEqual(list((self.root / ".video_encoder_trash").iterdir()), [])

    def test_retained_old_receipts_stay_intact_and_are_in_the_recovery_manifest(self):
        receipt = Path(str(self.source) + MODULE.SUFFIX)
        content = MODULE.encoded({"project_path": str(self.old), "output_path": str(self.source)})
        receipt.write_bytes(content)
        self.replace()
        original_job = self.jobs()[0]
        manifest = json.loads(Path(original_job[1]).parent.joinpath("manifest.json").read_text())
        self.assertEqual(Path(manifest[str(receipt)]).read_bytes(), content)
