import os
import unittest
import tempfile
import sqlite3
from unittest.mock import patch

import bcrypt
from app import app
import models.database as db_module


class TestAdminAuthentication(unittest.TestCase):
    """
    Comprehensive security and functionality test suite for the Admin Authentication System.
    Uses an isolated temporary SQLite database for every test to guarantee that
    the production tourism.db is never touched.
    """

    def setUp(self):
        # Create a fresh temporary database file for test isolation
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.temp_db_fd)

        # Point database module to the temporary database
        self.original_db_path = db_module.DB_PATH
        db_module.DB_PATH = self.temp_db_path

        # Setup test client
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False  # Allows direct POST testing without CSRF tokens
        self.client = app.test_client()

        # Seed initial test environment
        self.test_admin_user = "admin_test@example.com"
        self.test_admin_pass = "TestPassword#2026Safe!"
        self._init_test_db(self.test_admin_user, self.test_admin_pass)

    def tearDown(self):
        # Restore original database path and clean up temp file
        db_module.DB_PATH = self.original_db_path
        if os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
            except OSError:
                pass

    def _init_test_db(self, username, password):
        """Helper to initialize isolated schema and one admin user."""
        with db_module.get_db() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS places (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    city TEXT NOT NULL,
                    description TEXT,
                    history TEXT,
                    entry_fee TEXT,
                    opening_time TEXT,
                    closing_time TEXT,
                    best_season TEXT,
                    latitude REAL,
                    longitude REAL,
                    nearby_attractions TEXT,
                    nearby_restaurants TEXT,
                    nearby_hotels TEXT,
                    image_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    user_message TEXT,
                    bot_response TEXT,
                    language TEXT DEFAULT 'en',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS admin_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute(
                "INSERT INTO places (name, city) VALUES ('Test Sight', 'Chennai')"
            )
            pwd_hash = db_module._hash_password(password)
            conn.execute(
                "INSERT INTO admin_users (username, password_hash) VALUES (?, ?)",
                (username, pwd_hash),
            )

    # -------------------------------------------------------------------------
    # 1. Login Tests
    # -------------------------------------------------------------------------

    def test_successful_admin_login(self):
        """Valid admin credentials allow login and redirect to the dashboard."""
        response = self.client.post(
            "/admin/login",
            data={"username": self.test_admin_user, "password": self.test_admin_pass},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin", response.headers["Location"])

        with self.client.session_transaction() as sess:
            self.assertTrue(sess.get("logged_in"))
            self.assertEqual(sess.get("username"), self.test_admin_user)

    def test_failed_login_incorrect_password(self):
        """Incorrect password fails with generic message and does not establish session."""
        response = self.client.post(
            "/admin/login",
            data={"username": self.test_admin_user, "password": "WrongPassword123!"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Invalid credentials", response.data)

        with self.client.session_transaction() as sess:
            self.assertFalse(sess.get("logged_in", False))

    def test_failed_login_unknown_username(self):
        """Unknown username fails with generic message without leaking user existence."""
        response = self.client.post(
            "/admin/login",
            data={"username": "nonexistent_user@example.com", "password": "SomePassword123!"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Invalid credentials", response.data)

        with self.client.session_transaction() as sess:
            self.assertFalse(sess.get("logged_in", False))

    def test_failed_login_empty_credentials(self):
        """Empty username or password fails gracefully with generic error."""
        response = self.client.post(
            "/admin/login",
            data={"username": "", "password": ""},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Invalid credentials", response.data)

    # -------------------------------------------------------------------------
    # 2. Access Control Tests
    # -------------------------------------------------------------------------

    def test_protected_routes_without_authentication(self):
        """All administrative routes redirect to /admin/login when accessed unauthenticated."""
        protected_endpoints = [
            "/admin",
            "/admin/place/new",
            "/admin/change-password",
            "/admin/place/edit/1",
        ]
        for endpoint in protected_endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint, follow_redirects=False)
                self.assertEqual(response.status_code, 302)
                self.assertIn("/admin/login", response.headers["Location"])

    def test_protected_post_routes_without_authentication(self):
        """POST routes to admin endpoints reject unauthenticated requests."""
        response = self.client.post("/admin/place/delete/1", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login", response.headers["Location"])

    def test_protected_routes_after_authentication(self):
        """Authenticated admin can access all admin endpoints."""
        with self.client.session_transaction() as sess:
            sess["logged_in"] = True
            sess["username"] = self.test_admin_user

        response = self.client.get("/admin")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/admin/place/new")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/admin/change-password")
        self.assertEqual(response.status_code, 200)

    # -------------------------------------------------------------------------
    # 3. Logout & Session Invalidation
    # -------------------------------------------------------------------------

    def test_logout_and_session_invalidation(self):
        """Logging out clears session and prevents further access to protected routes."""
        with self.client.session_transaction() as sess:
            sess["logged_in"] = True
            sess["username"] = self.test_admin_user

        # Logout via POST
        response = self.client.post("/admin/logout", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login", response.headers["Location"])

        # Session should be empty
        with self.client.session_transaction() as sess:
            self.assertFalse(sess.get("logged_in", False))
            self.assertIsNone(sess.get("username"))

        # Subsequent attempt to access dashboard should redirect to login
        dash_response = self.client.get("/admin", follow_redirects=False)
        self.assertEqual(dash_response.status_code, 302)
        self.assertIn("/admin/login", dash_response.headers["Location"])

    # -------------------------------------------------------------------------
    # 4. Password Hashing and Timing Verification
    # -------------------------------------------------------------------------

    def test_password_hashing_bcrypt(self):
        """Password hashing generates valid bcrypt hashes with work factor 12."""
        raw_pwd = "SuperSecretPassword123!"
        hashed = db_module._hash_password(raw_pwd)

        self.assertTrue(hashed.startswith("$2b$12$") or hashed.startswith("$2a$12$"))
        self.assertTrue(db_module._verify_password(raw_pwd, hashed))
        self.assertFalse(db_module._verify_password("WrongPassword!", hashed))

    def test_legacy_or_invalid_hashes_rejected(self):
        """Plaintext or unrecognized hashes are rejected safely."""
        self.assertFalse(db_module._verify_password("test", "plain_text_not_a_hash"))
        self.assertFalse(db_module._verify_password("test", ""))

    def test_verify_admin_timing_mitigation_on_nonexistent_user(self):
        """verify_admin for an unknown user executes safely without throwing errors."""
        result = db_module.verify_admin("nonexistent_user", "AnyPassword123!")
        self.assertFalse(result)

    # -------------------------------------------------------------------------
    # 5. Seeding, Overwrite Protection, and Initial Account Logic
    # -------------------------------------------------------------------------

    def test_initial_admin_creation_with_env_password(self):
        """When admin_users is empty, seed_data creates initial admin with ADMIN_DEFAULT_PASSWORD."""
        # Wipe admin users in test db
        with db_module.get_db() as conn:
            conn.execute("DELETE FROM admin_users")

        with patch.dict(os.environ, {
            "ADMIN_EMAIL": "initial_admin@example.com",
            "ADMIN_DEFAULT_PASSWORD": "ConfiguredEnvPass123!"
        }):
            db_module.seed_data()

        self.assertTrue(
            db_module.verify_admin("initial_admin@example.com", "ConfiguredEnvPass123!")
        )

    def test_initial_admin_creation_generates_random_password_when_empty(self):
        """When admin_users is empty and no password is set, generates a random password, not hardcoded."""
        with db_module.get_db() as conn:
            conn.execute("DELETE FROM admin_users")

        with patch.dict(os.environ, {
            "ADMIN_EMAIL": "random_admin@example.com",
            "ADMIN_DEFAULT_PASSWORD": ""
        }):
            db_module.seed_data()

        # Must NOT be the old hardcoded default "Admin#SmartGuide2026!"
        self.assertFalse(
            db_module.verify_admin("random_admin@example.com", "Admin#SmartGuide2026!")
        )

    def test_restart_does_not_overwrite_existing_admin_password(self):
        """Subsequent restarts/seed_data calls MUST NOT overwrite existing admin credentials."""
        # Current test user is self.test_admin_user with self.test_admin_pass
        self.assertTrue(db_module.verify_admin(self.test_admin_user, self.test_admin_pass))

        # Simulate a server restart where ADMIN_DEFAULT_PASSWORD is set to something else
        with patch.dict(os.environ, {
            "ADMIN_EMAIL": self.test_admin_user,
            "ADMIN_DEFAULT_PASSWORD": "NewAttemptedPassword123!"
        }):
            db_module.seed_data()

        # The existing password MUST remain unchanged
        self.assertTrue(
            db_module.verify_admin(self.test_admin_user, self.test_admin_pass),
            "Existing admin password was silently overwritten on restart!"
        )
        # The new environment password should NOT have overwritten it
        self.assertFalse(
            db_module.verify_admin(self.test_admin_user, "NewAttemptedPassword123!")
        )

    def test_explicit_force_password_reset_env_var(self):
        """ADMIN_FORCE_PASSWORD_RESET=true explicitly allows intentional admin credential reset."""
        with patch.dict(os.environ, {
            "ADMIN_EMAIL": self.test_admin_user,
            "ADMIN_DEFAULT_PASSWORD": "ExplicitResetPassword123!",
            "ADMIN_FORCE_PASSWORD_RESET": "true"
        }):
            db_module.seed_data()

        # The password is now explicitly updated
        self.assertTrue(
            db_module.verify_admin(self.test_admin_user, "ExplicitResetPassword123!")
        )

    # -------------------------------------------------------------------------
    # 6. In-App Password Change Feature
    # -------------------------------------------------------------------------

    def test_in_app_password_change_success(self):
        """Authenticated admin can change their password through the web interface."""
        with self.client.session_transaction() as sess:
            sess["logged_in"] = True
            sess["username"] = self.test_admin_user

        new_password = "BrandNewSecurePassword2026!"
        response = self.client.post(
            "/admin/change-password",
            data={
                "current_password": self.test_admin_pass,
                "new_password": new_password,
                "confirm_password": new_password,
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Password updated successfully", response.data)

        # Old password no longer works
        self.assertFalse(db_module.verify_admin(self.test_admin_user, self.test_admin_pass))
        # New password works
        self.assertTrue(db_module.verify_admin(self.test_admin_user, new_password))

    def test_in_app_password_change_incorrect_current(self):
        """Password change fails when current password is wrong."""
        with self.client.session_transaction() as sess:
            sess["logged_in"] = True
            sess["username"] = self.test_admin_user

        response = self.client.post(
            "/admin/change-password",
            data={
                "current_password": "WrongCurrentPassword123!",
                "new_password": "ValidNewPassword2026!",
                "confirm_password": "ValidNewPassword2026!",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Current password is incorrect", response.data)
        # Original password still works
        self.assertTrue(db_module.verify_admin(self.test_admin_user, self.test_admin_pass))

    def test_in_app_password_change_too_short(self):
        """Password change rejects passwords under 12 characters."""
        with self.client.session_transaction() as sess:
            sess["logged_in"] = True
            sess["username"] = self.test_admin_user

        response = self.client.post(
            "/admin/change-password",
            data={
                "current_password": self.test_admin_pass,
                "new_password": "short",
                "confirm_password": "short",
            },
            follow_redirects=True,
        )
        self.assertIn(b"at least 12 characters", response.data)

    def test_in_app_password_change_mismatch(self):
        """Password change rejects mismatched new passwords."""
        with self.client.session_transaction() as sess:
            sess["logged_in"] = True
            sess["username"] = self.test_admin_user

        response = self.client.post(
            "/admin/change-password",
            data={
                "current_password": self.test_admin_pass,
                "new_password": "ValidNewPassword2026!",
                "confirm_password": "DifferentPassword2026!",
            },
            follow_redirects=True,
        )
        self.assertIn(b"do not match", response.data)

    # -------------------------------------------------------------------------
    # 7. CLI / Helper Password Update
    # -------------------------------------------------------------------------

    def test_cli_update_admin_password_function(self):
        """update_admin_password function securely updates user password."""
        new_pwd = "CliUpdatedPassword123!"
        success = db_module.update_admin_password(self.test_admin_user, new_pwd)
        self.assertTrue(success)
        self.assertTrue(db_module.verify_admin(self.test_admin_user, new_pwd))

        # Nonexistent user returns False
        self.assertFalse(db_module.update_admin_password("ghost_user", new_pwd))

    # -------------------------------------------------------------------------
    # 8. Record Preservation
    # -------------------------------------------------------------------------

    def test_existing_places_records_preserved(self):
        """Places table records are never wiped or lost during re-initialization."""
        with db_module.get_db() as conn:
            count_before = conn.execute("SELECT COUNT(*) FROM places").fetchone()[0]

        # Re-run init_db and seed_data
        db_module.init_db()
        db_module.seed_data()

        with db_module.get_db() as conn:
            count_after = conn.execute("SELECT COUNT(*) FROM places").fetchone()[0]

        self.assertGreaterEqual(count_after, count_before)


if __name__ == "__main__":
    unittest.main()

