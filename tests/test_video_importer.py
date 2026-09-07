import unittest
import json
import os
from app import app
import video_importer

class TestVideoImporter(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_lectures_index(self):
        lectures = video_importer.get_lectures_index()
        self.assertIsInstance(lectures, list)
        self.assertGreaterEqual(len(lectures), 1)
        self.assertEqual(lectures[0]['id'], 'tedtalk')

    def test_sanitize_filename(self):
        dirty = 'My Cool Lecture? &* Special!! (2026).mp4'
        clean = video_importer.sanitize_filename(dirty)
        self.assertNotIn('?', clean)
        self.assertNotIn('&', clean)
        self.assertNotIn('*', clean)

    def test_api_lectures_endpoint(self):
        res = self.client.get('/api/practice/lectures')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn('lectures', data)
        self.assertTrue(any(l['id'] == 'tedtalk' for l in data['lectures']))

    def test_api_import_url_validation(self):
        # Empty URL should return 400
        res = self.client.post('/api/practice/import-url', 
                               data=json.dumps({'url': ''}),
                               content_type='application/json')
        self.assertEqual(res.status_code, 400)

if __name__ == '__main__':
    unittest.main()
