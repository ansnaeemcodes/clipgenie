"""
tests/test_native_auth_and_progress.py
Comprehensive automated test suite for native SQLite auth, password hashing,
and persistent student concept mastery tracking.
"""

import unittest
import json
import os
import database
from app import app

class TestNativeAuthAndProgress(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True
        database.init_db()

    def test_database_create_and_verify_user(self):
        """Tests user creation with scrypt password hashing and credential verification."""
        test_email = "test.student@example.com"
        # Cleanup if exists
        conn = database.get_db_connection()
        conn.execute("DELETE FROM users WHERE email = ?", (test_email,))
        conn.commit()
        conn.close()

        user, err = database.create_user(
            email=test_email,
            password="SecurePassword123!",
            first_name="Jordan",
            last_name="Tester"
        )
        self.assertIsNone(err)
        self.assertIsNotNone(user)
        self.assertEqual(user["email"], test_email)
        self.assertEqual(user["displayName"], "Jordan Tester")

        # Verify correct credentials
        verified, err = database.verify_user(test_email, "SecurePassword123!")
        self.assertIsNone(err)
        self.assertIsNotNone(verified)
        self.assertEqual(verified["email"], test_email)

        # Verify incorrect credentials
        wrong, err = database.verify_user(test_email, "WrongPassword!")
        self.assertIsNotNone(err)
        self.assertIsNone(wrong)

        # Duplicate email rejected
        dup, err = database.create_user(test_email, "Password999!", "Copy", "Cat")
        self.assertIsNotNone(err)
        self.assertIn("already exists", err.lower())

    def test_flask_auth_endpoints(self):
        """Tests Flask /register and /login endpoints end-to-end via JSON API."""
        api_email = "api.learner@example.com"
        conn = database.get_db_connection()
        conn.execute("DELETE FROM users WHERE email = ?", (api_email,))
        conn.commit()
        conn.close()

        # 1. Register
        res_reg = self.client.post('/register', json={
            'email': api_email,
            'password': 'ApiPassword123!',
            'firstName': 'Taylor',
            'lastName': 'Student'
        })
        self.assertEqual(res_reg.status_code, 201)
        data_reg = json.loads(res_reg.data)
        self.assertTrue(data_reg.get('success'))
        self.assertEqual(data_reg['user']['email'], api_email)

        # 2. Login
        res_login = self.client.post('/login', json={
            'email': api_email,
            'password': 'ApiPassword123!'
        })
        self.assertEqual(res_login.status_code, 200)
        data_login = json.loads(res_login.data)
        self.assertTrue(data_login.get('success'))
        self.assertEqual(data_login['user']['email'], api_email)

        # 3. Invalid Login
        res_bad = self.client.post('/login', json={
            'email': api_email,
            'password': 'BadPassword!'
        })
        self.assertEqual(res_bad.status_code, 401)

    def test_progress_persistence_and_independence_calculation(self):
        """Tests saving and retrieving concept mastery records in SQLite."""
        # Log in as demo user
        res_demo = self.client.get('/demo-login')
        self.assertEqual(res_demo.status_code, 302)

        # Save progress for concept_3
        res_save = self.client.post('/api/practice/save-progress', json={
            'video_id': 'tedtalk',
            'concept_id': 'concept_3',
            'concept_title': 'Self-Refining Systems',
            'attempt1_score': 85,
            'attempt2_score': 0,
            'transfer_score': 90,
            'mastery_status': 'Mastered',
            'handled_without_help': 1
        })
        self.assertEqual(res_save.status_code, 200)
        data_save = json.loads(res_save.data)
        self.assertTrue(data_save.get('saved'))

        # Retrieve saved progress
        res_prog = self.client.get('/api/practice/user-progress?video_id=tedtalk')
        self.assertEqual(res_prog.status_code, 200)
        data_prog = json.loads(res_prog.data)
        self.assertTrue(data_prog.get('authenticated'))
        self.assertIn('concept_3', data_prog['concepts'])
        self.assertEqual(data_prog['concepts']['concept_3']['mastery_status'], 'Mastered')
        self.assertIn('%', data_prog['independence_rate'])

if __name__ == '__main__':
    unittest.main()
