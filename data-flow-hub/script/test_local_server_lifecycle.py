"""Verify the local release permits one server and reports real database readiness."""
import unittest
import test_app as fixtures
from database import acquire_server_lock, database_url
from release_version import VERSION, DEPLOYMENT


@unittest.skipUnless(database_url(), "PostgreSQL server guard requires isolated PostgreSQL tests.")
class LocalServerLifecycleTests(unittest.TestCase):
    def test_server_lock_is_exclusive_and_released_on_close(self):
        first = acquire_server_lock()
        try:
            with self.assertRaisesRegex(RuntimeError, 'already running'):
                acquire_server_lock()
        finally:
            first.close()
        again = acquire_server_lock()
        again.close()

    def test_health_checks_database_and_declares_release_scope(self):
        response = fixtures.module.app.test_client().get('/api/v1/health')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json['success'])
        self.assertEqual(response.json['database'], 'postgresql')
        self.assertEqual(response.json['version'], VERSION)
        self.assertEqual(response.json['deployment'], DEPLOYMENT)


if __name__ == '__main__':
    unittest.main()
