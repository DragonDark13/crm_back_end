import unittest
from scripts.database_backup import database_connection_env


class DatabaseBackupConnectionTests(unittest.TestCase):
    def test_parses_postgres_url_without_exposing_password_in_args(self):
        args, env = database_connection_env(
            "postgresql://crm_user:p%40ss%3Aword@db.example:5433/crm?sslmode=require"
        )

        self.assertEqual(args, ["--dbname", "crm", "--host", "db.example", "--port", "5433", "--username", "crm_user"])
        self.assertEqual(env["PGPASSWORD"], "p@ss:word")
        self.assertEqual(env["PGSSLMODE"], "require")
        self.assertNotIn("p@ss:word", " ".join(args))

    def test_rejects_non_postgres_database_url(self):
        with self.assertRaises(ValueError):
            database_connection_env("sqlite:///crm.db")


if __name__ == "__main__":
    unittest.main()
