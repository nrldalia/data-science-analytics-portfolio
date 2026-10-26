"""Credential-safe native PostgreSQL configuration; no database writes."""
import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import unquote, urlsplit

from dotenv import dotenv_values
import configure_native_database as setup


class NativeDatabaseSetupTests(unittest.TestCase):
    def test_special_characters_round_trip_without_dotenv_interpolation(self):
        password = "quotes'and\"hash#dollar$at@colon:slash/percent%space "
        url = setup.build_url('127.0.0.1', '5432', 'demo db', 'demo@user', password)
        parsed = urlsplit(url)
        self.assertEqual(unquote(parsed.password), password)
        self.assertEqual(unquote(parsed.username), 'demo@user')
        self.assertEqual(unquote(parsed.path[1:]), 'demo db')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'.env'
            setup.save_url(url, path)
            self.assertEqual(dotenv_values(path)['DATABASE_URL'], url)

    def test_local_host_and_invalid_port_or_control_characters(self):
        for host in ['remote.example.com', '127.0.0.1\n']:
            with self.subTest(host=host), self.assertRaises(ValueError):
                setup.build_url(host,5432,'dataflow','dataflow','fake-password')
        for port in [0,65536,True,'5432\n','invalid']:
            with self.subTest(port=port), self.assertRaises(ValueError):
                setup.build_url('localhost',port,'dataflow','dataflow','fake-password')
        with self.assertRaises(ValueError):
            setup.build_url('localhost',5432,'dataflow','dataflow','bad\npassword')
        self.assertEqual(urlsplit(setup.build_url('::1',5432,'dataflow','dataflow','fake-password')).hostname,'::1')

    def test_existing_file_never_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'.env';path.write_text('UNCHANGED=yes\n')
            with self.assertRaises(FileExistsError):
                setup.save_url(setup.build_url('localhost',5432,'dataflow','dataflow','fake-password'),path)
            self.assertEqual(path.read_text(),'UNCHANGED=yes\n')

    def test_check_missing_settings_does_not_prompt_or_write(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ,{},clear=True), patch.object(setup,'ENV_FILE',Path(folder)/'.env'), patch('builtins.input') as prompt, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(setup.main(['--check']),1)
            prompt.assert_not_called()
            self.assertFalse(setup.ENV_FILE.exists())

    def test_failed_connection_does_not_save_or_echo_credentials(self):
        output=io.StringIO()
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ,{},clear=True), patch.object(setup,'ENV_FILE',Path(folder)/'.env'), patch('builtins.input',side_effect=['','','','']), patch.object(setup.getpass,'getpass',return_value='DO-NOT-ECHO-SECRET'), patch.object(setup.psycopg,'connect',side_effect=setup.psycopg.OperationalError('DO-NOT-ECHO-SECRET')), contextlib.redirect_stdout(output):
            self.assertEqual(setup.main([]),1)
            self.assertFalse(setup.ENV_FILE.exists())
        self.assertNotIn('DO-NOT-ECHO-SECRET',output.getvalue())

    def test_verified_connection_is_saved_and_reused_without_prompt(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ,{},clear=True), patch.object(setup,'ENV_FILE',Path(folder)/'.env'), patch.object(setup,'check_connection') as check, patch('builtins.input',side_effect=['','','','']), patch.object(setup.getpass,'getpass',return_value='fake@password#only'), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(setup.main([]),0)
            before=setup.ENV_FILE.read_bytes()
            self.assertEqual(check.call_count,1)
            with patch('builtins.input') as prompt:
                self.assertEqual(setup.main(['--check']),0)
                prompt.assert_not_called()
            self.assertEqual(setup.ENV_FILE.read_bytes(),before)

    def test_process_url_precedence_and_legacy_mode_rejection(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'.env';path.write_text("DATABASE_URL='postgresql://file-value/db'\n")
            with patch.dict(os.environ,{'DATABASE_URL':'postgresql://process-value/db'},clear=True):
                self.assertEqual(setup.configured_url(path),'postgresql://process-value/db')
            with patch.dict(os.environ,{'DATAFLOW_DB':'legacy.db'},clear=True), self.assertRaises(ValueError):
                setup.configured_url(path)


if __name__ == '__main__':
    unittest.main()
