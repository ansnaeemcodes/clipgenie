import unittest
import learning_loop
import concept_detector
import groq_transcription

class TestLearningLoopPipeline(unittest.TestCase):
    """
    Tests full pipeline: Concept Extraction -> Prompt Generation ->
    Feedback -> Retry Comparison -> Transfer Check -> Mastery.
    """

    def setUp(self):
        self.segments = [
            {"start": 26.16, "end": 45.12, "text": "We cannot control what we don't understand."},
            {"start": 45.12, "end": 76.84, "text": "And so the metaphors and mental models all matter. We'll come to see them as digital companions."}
        ]
        self.concept_id = "concept_1"
        self.concept_title = "The AI Inflection Point & Digital Companions"
        self.transcript = "We cannot control what we don't understand. Metaphors matter. Digital companions."

    def test_concept_extraction(self):
        concepts = concept_detector.get_lecture_concepts("tedtalk.mp4", self.segments, force_auto=False)
        self.assertGreater(len(concepts), 0)
        self.assertEqual(concepts[0]["id"], "concept_1")
        self.assertIn("start", concepts[0])
        self.assertIn("end", concepts[0])

    def test_prompt_generation(self):
        prompt_data = learning_loop.generate_retrieval_prompt(
            self.concept_id, self.concept_title, self.transcript, mode="offline"
        )
        self.assertIn("question", prompt_data)
        self.assertGreater(len(prompt_data["question"]), 20)

    def test_retry_scoring_delta(self):
        attempt_1_text = "Metaphors matter."
        attempt_2_text = "Metaphors matter because we cannot control what we do not understand, so seeing AI as digital companions creates the right mental model."
        
        retry_result = learning_loop.evaluate_retry(
            concept_id=self.concept_id,
            attempt_1_score=35,
            attempt_1_answer=attempt_1_text,
            attempt_2_answer=attempt_2_text,
            transcript_text=self.transcript,
            mode="offline"
        )
        self.assertIn("delta", retry_result)
        self.assertIn("comparison_message", retry_result)
        self.assertGreaterEqual(retry_result["delta"], 0)

    def test_transfer_check_question(self):
        transfer = learning_loop.generate_transfer_question(
            self.concept_id, self.concept_title, self.transcript, mode="offline"
        )
        self.assertIn("transfer_question", transfer)
        # Verify transfer question is distinct and tests application
        self.assertIn("hospital", transfer["transfer_question"].lower())

    def test_transfer_evaluation(self):
        transfer_eval = learning_loop.evaluate_transfer_answer(
            concept_id=self.concept_id,
            transfer_question="How should hospital staff reframe AI?",
            student_answer="They should view it as a collaborative diagnostic partner so they critically evaluate it instead of assuming it is an infallible calculator spreadsheet.",
            transcript_text=self.transcript,
            mode="offline"
        )
        self.assertIn("transfer_score", transfer_eval)
        self.assertIn("transfer_mastery", transfer_eval)
        self.assertGreaterEqual(transfer_eval["transfer_score"], 50)

if __name__ == '__main__':
    unittest.main()
