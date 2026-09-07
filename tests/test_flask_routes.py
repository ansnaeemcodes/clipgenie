import unittest
from app import app
import json

class TestFlaskEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_pages_render(self):
        res_practice = self.client.get('/practice')
        self.assertEqual(res_practice.status_code, 200)
        self.assertIn(b'Practice Loop', res_practice.data)

        res_instructor = self.client.get('/instructor')
        self.assertEqual(res_instructor.status_code, 200)
        self.assertIn(b'Cohort Mastery', res_instructor.data)

    def test_api_practice_load(self):
        res = self.client.get('/api/practice/load?mode=offline')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn('concepts', data)
        self.assertGreater(len(data['concepts']), 0)

    def test_api_prompt_and_feedback(self):
        # 1. Prompt
        res_prompt = self.client.post('/api/practice/generate-prompt', json={
            'concept_id': 'concept_1',
            'concept_title': 'Inflection Point',
            'start': 26.16,
            'end': 76.84,
            'mode': 'offline'
        })
        self.assertEqual(res_prompt.status_code, 200)
        prompt_data = json.loads(res_prompt.data)
        self.assertIn('question', prompt_data)

        # 2. Gap Feedback
        res_fb = self.client.post('/api/practice/feedback', json={
            'concept_id': 'concept_1',
            'question': prompt_data['question'],
            'student_answer': 'AI is becoming like a companion rather than just software.',
            'start': 26.16,
            'end': 76.84,
            'mode': 'offline'
        })
        self.assertEqual(res_fb.status_code, 200)
        fb_data = json.loads(res_fb.data)
        self.assertIn('score', fb_data)
        self.assertIn('conceptual_hint', fb_data)
        self.assertFalse(fb_data.get('revealed_answer', False))

if __name__ == '__main__':
    unittest.main()
