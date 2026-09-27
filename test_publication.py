"""Exercise the final move without replacing a competing destination."""

import errno
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from desktop import publish_clip


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        scratch = root / ".clip-test"
        scratch.mkdir()
        self.temporary = scratch / "clip.mp4"
        self.destination = root / "finished.mp4"
        self.temporary.write_bytes(b"verified clip")

    def test_windows_publication_does_not_require_hard_links(self):
        # The host rename is real; only platform choice and link support vary.
        with patch("desktop.sys.platform", "win32"), patch(
            "desktop.os.link", side_effect=OSError(errno.ENOTSUP, "no hard links")
        ):
            publish_clip(self.temporary, self.destination)
        self.assertEqual(self.destination.read_bytes(), b"verified clip")
        self.assertFalse(self.temporary.exists())

    def test_existing_destination_survives_native_publication(self):
        self.destination.write_bytes(b"another writer's file")
        with self.assertRaises(FileExistsError):
            publish_clip(self.temporary, self.destination)
        self.assertEqual(self.destination.read_bytes(), b"another writer's file")
        self.assertEqual(self.temporary.read_bytes(), b"verified clip")

    def test_failed_windows_move_keeps_temporary_file(self):
        with patch("desktop.sys.platform", "win32"), patch(
            "desktop.os.rename", side_effect=PermissionError("read-only folder")
        ), self.assertRaises(PermissionError):
            publish_clip(self.temporary, self.destination)
        self.assertFalse(self.destination.exists())
        self.assertEqual(self.temporary.read_bytes(), b"verified clip")

    def test_successful_native_publication_preserves_bytes(self):
        publish_clip(self.temporary, self.destination)
        self.assertEqual(self.destination.read_bytes(), b"verified clip")
        self.assertFalse(self.temporary.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
