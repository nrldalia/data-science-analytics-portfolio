"""Windows checkout regression: equivalent endings pass, edited data fails."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import generate_store_demo as generator
import load_store_demo as loader


class DemoLineEndingTests(unittest.TestCase):
    def test_crlf_checkout_matches_original_plan(self):
        baseline = loader.load_plan()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name, data in generator.build_files().items():
                (root / name).write_bytes(data.replace(b'\n', b'\r\n'))
            with patch.object(loader, 'FIXTURES', root):
                self.assertEqual(loader.load_plan(), baseline)

    def test_content_edits_still_fail_for_both_line_endings(self):
        for ending in (b'\n', b'\r\n'):
            with self.subTest(ending=ending), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                for name, data in generator.build_files().items():
                    if name == 'demo_aurora_stores.csv':
                        data = data.replace(b'Aurora Demo Kuala Lumpur 001', b'Changed Store Name 001', 1)
                    (root / name).write_bytes(data.replace(b'\n', ending))
                with patch.object(loader, 'FIXTURES', root), self.assertRaisesRegex(ValueError, 'fingerprint'):
                    loader.load_plan()

    def test_generator_preserves_equivalent_windows_checkout(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / 'fixtures'
            output.mkdir()
            files = generator.build_files()
            for name, data in files.items():
                (output / name).write_bytes(data.replace(b'\n', b'\r\n'))
            before = {p.name: p.read_bytes() for p in output.iterdir()}
            with patch.object(generator, 'PROJECT_ROOT', root):
                generator.generate(output)
                self.assertEqual({p.name: p.read_bytes() for p in output.iterdir()}, before)
                target = output / 'demo_aurora_stores.csv'
                target.write_bytes(target.read_bytes().replace(b'Aurora Demo', b'Edited Demo', 1))
                with self.assertRaisesRegex(ValueError, 'overwrite changed file'):
                    generator.generate(output)


if __name__ == '__main__':
    unittest.main()
