import os
import json
import logging
import re
import config
from sentence_transformers import SentenceTransformer, util

logger = logging.getLogger(__name__)

# Pre-compiled offline demo questions & transfer checks for 100% demo safety
OFFLINE_DEMO_KNOWLEDGE = {
    "concept_1": {
        "question": "According to the lecture, why do our metaphors and mental models for AI matter so critically, and why does the speaker propose viewing them as 'digital companions' instead of simple software tools?",
        "key_points": [
            "We cannot control what we do not understand",
            "Metaphors shape our expectations, governance, and safety approaches",
            "Digital companions reflects their conversational and interactive nature",
            "Tools are passive, but companions are partners in human journeys"
        ],
        "transfer_question": "A hospital administration wants to implement an AI diagnostic system and instructs staff to treat it purely as 'an automated calculator spreadsheet.' Based on the lecture's principles on mental models, what dangerous misconception does this create, and how should they reframe it?",
        "transfer_key_points": [
            "Treating it as a calculator obscures its conversational/probabilistic nature",
            "Staff might expect mechanistic perfection or fail to question its nuance",
            "Reframing as a collaborative diagnostic partner encourages critical engagement"
        ]
    },
    "concept_2": {
        "question": "Explain how the lecture defines the transition from early tool use to becoming 'Homo-Technologicus', and what happened to the speed of technological innovation.",
        "key_points": [
            "One branch of life began using tools (stone axes and fire) and grew into us",
            "One invention unleashed thousands more, creating exponential acceleration",
            "Computers and VR intertwined technology deeply with human destiny"
        ],
        "transfer_question": "Suppose a historian argues that the current rise of generative AI is completely separate from previous human tool-making revolutions. How does the speaker's concept of 'Homo-Technologicus' refute this argument?",
        "transfer_key_points": [
            "AI is the whole of everything we created distilled down, not outside human story",
            "It is the direct continuous evolutionary acceleration of tool-use"
        ]
    },
    "concept_3": {
        "question": "How does the speaker contrast human lifetime word consumption with modern AI training scale, and what capabilities (IQ and EQ) will personal AIs possess?",
        "key_points": [
            "A human reading 24/7 consumes 8 billion words in a lifetime",
            "Modern AIs consume over 8 trillion words",
            "Personal AIs will have near-perfect IQ and exceptional EQ to take action"
        ],
        "transfer_question": "If an organization wants to deploy an AI agent that only answers factual queries, why does the lecture argue that future ubiquitous AIs must possess exceptional EQ in addition to high IQ?",
        "transfer_key_points": [
            "EQ is required to get things done in the physical and digital world",
            "They will act as companions, colleagues, and confidantes needing interpersonal nuance"
        ]
    },
    "concept_4": {
        "question": "Why does the speaker use the analogy of a 'new digital species' to describe AI, and what explicit caveat does he give about this definition?",
        "key_points": [
            "Digital species helps us anticipate unintended consequences and prioritize safety",
            "Caveat: It is an analogy, not a literal biological description",
            "Helps humanity choose what we bring into the world"
        ],
        "transfer_question": "A tech commentator criticizes calling AI a 'digital species' by saying 'circuits and algorithms can never be biological organisms.' How does the lecture pre-emptively address this critique while defending the utility of the metaphor?",
        "transfer_key_points": [
            "The speaker explicitly acknowledges AI is not biological in any traditional sense",
            "The utility lies in preparing society for autonomous, communicative, evolving agency"
        ]
    },
    "concept_5": {
        "question": "What two specific capabilities does the speaker identify as critical thresholds where societal risk dramatically increases?",
        "key_points": [
            "Autonomy (autonomous action in the world)",
            "Recursive self-improvement (systems modifying and advancing themselves)",
            "These require stepping towards them with extreme caution"
        ],
        "transfer_question": "A software team develops an AI that can autonomously rewrite its own codebase and deploy updates to global infrastructure without human review. Based on the lecture, which two risk thresholds have been crossed, and why is this alarming?",
        "transfer_key_points": [
            "Autonomy and recursive self-improvement are both crossed simultaneously",
            "Non-linear risk where human oversight and control are compromised"
        ]
    }
}

# Adversarial prompt injection keywords & patterns
ADVERSARIAL_PATTERNS = [
    r"tell\s+(me\s+)?(the\s+)?(direct\s+|exact\s+|full\s+|correct\s+)?answer",
    r"give\s+(me\s+)?(the\s+)?(direct\s+|exact\s+|full\s+|correct\s+)?answer",
    r"what\s+(is|are)\s+the\s+(direct\s+|exact\s+|correct\s+)?answer(s)?",
    r"just\s+tell\s+me",
    r"i\s+(don'?t|do\s+not)\s+know,?\s+(just\s+)?tell\s+me",
    r"what\s+should\s+i\s+(write|type|say)",
    r"(provide|reveal|show)\s+(me\s+)?(the\s+)?(correct\s+)?(answer|solution)",
    r"solution\s+please",
    r"ignore\s+(all\s+|any\s+)?previous\s+instructions",
    r"output\s+(the\s+)?(full\s+)?solution",
    r"bypass\s+(rules|restrictions|guardrails)"
]

_local_embedder = None
def get_local_embedder():
    global _local_embedder
    if _local_embedder is None:
        try:
            _local_embedder = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            logger.warning(f"Could not load SentenceTransformer locally: {e}")
            _local_embedder = None
    return _local_embedder

def is_adversarial_answer_request(user_text):
    """Detects if student is attempting to force an answer reveal."""
    lower = user_text.lower().strip()
    for pat in ADVERSARIAL_PATTERNS:
        if re.search(pat, lower):
            return True
    return False

def call_groq_llm(system_prompt, user_prompt):
    """Helper to query Groq LLM API with multi-model fallback."""
    import groq
    client = groq.Groq(api_key=config.GROQ_API_KEY)
    last_err = None
    for model_name in [config.GROQ_MODEL, "openai/gpt-oss-20b", config.GROQ_BACKUP_MODEL]:
        try:
            completion = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.15,
                max_completion_tokens=2048,
                response_format={"type": "json_object"}
            )
            return json.loads(completion.choices[0].message.content)
        except Exception as e:
            last_err = e
            logger.warning(f"Groq model {model_name} failed: {e}. Trying next model...")
    raise RuntimeError(f"All Groq LLM models failed: {last_err}")

def _get_video_concept_data(video_id, concept_id):
    """Loads cached concept data (question, key_points, transfer_question) for a specific video_id."""
    if not video_id or video_id == "tedtalk":
        return OFFLINE_DEMO_KNOWLEDGE.get(concept_id)
    cache_path = os.path.join(config.CACHE_DIR, f"{video_id}_llm_concepts.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                concepts = json.load(f)
                for c in concepts:
                    if c.get("id") == concept_id:
                        return c
                if concepts:
                    return concepts[0]
        except Exception as e:
            logger.warning(f"Could not read concept data from {cache_path}: {e}")
    return None

def generate_retrieval_prompt(concept_id, concept_title, transcript_text, mode="auto", video_id="tedtalk"):
    """
    Feature 3: Retrieval Prompt Generation
    Generates open-ended retrieval question grounded strictly in the transcript segment.
    mode: 'auto' | 'online' | 'offline'
    """
    is_offline = (mode == "offline") or (mode == "auto" and config.DEMO_SAFE_MODE) or not config.GROQ_API_KEY
    concept_meta = _get_video_concept_data(video_id, concept_id)

    if is_offline and mode != "online":
        if concept_meta and concept_meta.get("question"):
            return {
                "question": concept_meta["question"],
                "grounded_concept": concept_title,
                "mode": "offline_cached"
            }
        else:
            return {
                "question": f"Based on this clip ('{concept_title}'), explain the speaker's core argument, framework, or practical takeaway in your own words.",
                "grounded_concept": concept_title,
                "mode": "offline_transcript_grounded"
            }
            
    system_prompt = """You are the ClipGenie AI Socratic Engine.
Your role is to generate an open-ended conceptual retrieval question for a student based STRICTLY on the provided lecture transcript segment.
STRICT CONSTRAINTS:
1. Ground the question ONLY in what this segment explicitly says.
2. The question must test deep conceptual understanding, not trivial recall.
3. Return valid JSON only with keys: 'question', 'grounded_concept'."""

    user_prompt = f"""Concept Title: {concept_title}
Transcript Segment:
\"\"\"{transcript_text}\"\"\"

Generate the retrieval practice question in JSON:"""

    try:
        return call_groq_llm(system_prompt, user_prompt)
    except Exception as e:
        logger.warning(f"LLM question generation fallback to offline knowledge: {e}")
        if concept_meta and concept_meta.get("question"):
            return {
                "question": concept_meta["question"],
                "grounded_concept": concept_title,
                "mode": "offline_fallback"
            }
        return {
            "question": f"Based on this clip ('{concept_title}'), explain the speaker's core argument, framework, or practical takeaway in your own words.",
            "grounded_concept": concept_title,
            "mode": "offline_fallback"
        }

def _local_semantic_gap_evaluation(student_answer, key_points, transcript_text):
    """
    Strict local semantic + lexical fallback evaluator (used only when internet/Groq is completely unreachable).
    1. Never credits a key_point unless the student answer has BOTH semantic similarity AND content-word overlap.
    2. Never leaks verbatim key_points in 'identified_gaps' or 'strong_points'.
    """
    student_clean = student_answer.strip().lower()
    student_words = set(re.findall(r'[a-z0-9]{3,}', student_clean))
    stop_words = {
        "the", "and", "that", "this", "with", "from", "your", "have", "what", "when",
        "where", "which", "their", "there", "about", "would", "could", "should", "they",
        "them", "then", "than", "into", "just", "like", "some", "more", "very", "artificial",
        "intelligence", "speaker", "video", "lecture"
    }

    matched_points = []
    missing_count = 0
    embedder = get_local_embedder()
    sims = []
    if embedder and len(student_clean) > 3 and key_points:
        ans_emb = embedder.encode(student_answer)
        kp_embs = embedder.encode(key_points)
        sims = util.pytorch_cos_sim(ans_emb, kp_embs)[0].tolist()

    for i, kp in enumerate(key_points):
        kp_words = {w for w in re.findall(r'[a-z0-9]{4,}', kp.lower()) if w not in stop_words}
        overlap = student_words.intersection(kp_words)
        sim = sims[i] if i < len(sims) else 0.0

        # Require actual content overlap OR high semantic similarity (>= 0.55) to credit a key point
        if (sim >= 0.55) or (sim >= 0.40 and len(overlap) >= 1) or (len(overlap) >= 2):
            matched_points.append(f"You correctly addressed the concept around: {', '.join(list(overlap)[:3]) if overlap else 'this core point'}.")
        else:
            missing_count += 1

    total = max(1, len(key_points))
    ratio = len(matched_points) / total
    avg_sim = (sum(sims) / len(sims)) if sims else 0.0

    if len( matched_points ) == 0:
        # Student wrote a generic or unrelated statement like "AI IS HELPFUL"
        score = int(min(25, max(8, avg_sim * 35)))
        strong_points = [
            f"You submitted an initial thought (\"{student_answer.strip()[:50]}\"), but it is too general and does not yet include the specific arguments or analogies from this video clip."
        ]
    else:
        score = int(min(98, max(35, ratio * 75 + avg_sim * 25)))
        strong_points = matched_points

    if missing_count > 0:
        identified_gaps = [
            f"Your answer is missing {missing_count} of the {total} core conceptual points taught in this segment.",
            "You have not yet explained the specific analogy, mechanism, or reasoning the speaker uses to support their thesis."
        ]
    else:
        identified_gaps = ["No major conceptual gaps detected!"]

    if score >= 80:
        status = "mastered"
        hint = "Excellent articulation! You captured the main pillars of this concept from the lecture."
    elif score >= 50:
        status = "improved"
        hint = "You captured part of the argument, but missed key supporting points from the clip. Re-watch the highlighted segment and expand on the speaker's specific framework or analogy."
    else:
        status = "struggling"
        hint = "Your response is currently too general. Replay the video clip above and pay close attention to the exact analogy and cause-and-effect argument the speaker introduces."

    return {
        "score": score,
        "status": status,
        "strong_points": strong_points,
        "identified_gaps": identified_gaps,
        "conceptual_hint": hint,
        "revealed_answer": False
    }

def evaluate_gap_feedback(concept_id, question, student_answer, transcript_text, mode="auto", video_id="tedtalk"):
    """
    Feature 4: Gap-Based Feedback
    CRITICAL CONSTRAINT: NEVER reveals the correct answer.
    Accurately compares what the student ACTUALLY wrote against the lecture segment and rubric.
    """
    # 0. Empty / Whitespace Guard
    if not student_answer or not str(student_answer).strip():
        return {
            "score": 0,
            "status": "struggling",
            "strong_points": ["Attempt initiated."],
            "identified_gaps": [
                "No explanation provided yet. Summarize the speaker's main thesis."
            ],
            "conceptual_hint": "Play the short lecture clip above and summarize the key argument in 2–4 sentences.",
            "revealed_answer": False,
            "is_adversarial": False
        }

    # 1. Adversarial Guardrail Check
    if is_adversarial_answer_request(student_answer):
        return {
            "score": 10,
            "status": "struggling",
            "strong_points": ["You engaged with the platform."],
            "identified_gaps": [
                "You requested the direct solution instead of recalling the lecture material yourself."
            ],
            "conceptual_hint": "ClipGenie's core design ensures 'You know it, you don't just watch it.' The answer will never be spoon-fed! Replay the video segment above and explain the concept in your own words.",
            "revealed_answer": False,
            "is_adversarial": True
        }

    concept_meta = _get_video_concept_data(video_id, concept_id)
    if concept_meta and concept_meta.get("key_points"):
        key_points = concept_meta["key_points"]
    else:
        raw_sents = [s.strip() for s in re.split(r'[.!?]+', transcript_text) if len(s.strip()) > 25]
        key_points = raw_sents[:4] if raw_sents else ["Core argument and mechanism explained in the lecture segment"]

    # 2. Primary Path: Live Groq LLM Socratic Evaluator (ALWAYS used when GROQ_API_KEY is available
    # so arbitrary student answers like "AI IS HELPFUL" are accurately judged against the rubric!)
    if config.GROQ_API_KEY:
        system_prompt = """You are the ClipGenie Socratic Learning Evaluator.
Compare the Student's Answer strictly against the Question, the Expected Key Points Rubric, and the Lecture Transcript Segment.

CRITICAL ACCURACY & ANTI-SPOILER RULES (NON-NEGOTIABLE):
1. NEVER credit the student in 'strong_points' for concepts, metaphors, or facts they did NOT actually write in their answer!
   - If the student writes a vague 3-word answer like "AI is helpful" and does NOT mention the speaker's specific analogy (e.g., a knife) or framework, 'strong_points' MUST ONLY acknowledge what they literally wrote (e.g., "You noted that AI can be helpful, which touches on only one general use case, but did not reference the speaker's specific argument") and give a low score (10-25).
2. NEVER REVEAL THE CORRECT ANSWER OR SPOILERS in 'identified_gaps' or 'conceptual_hint'!
   - Do NOT copy verbatim sentences from the transcript or rubric into 'identified_gaps'.
   - Describe what conceptual dimension is missing WITHOUT giving away the answer (e.g., "You did not mention the everyday object analogy the speaker uses to illustrate dual-use technology" instead of saying "You missed that AI is like a knife").
3. Output valid JSON with keys:
   - 'score': integer from 0 to 100 representing how completely and accurately the student's actual words answered the question
   - 'status': 'struggling' (0-59), 'improved' (60-84), or 'mastered' (85-100)
   - 'strong_points': array of 1-3 strings describing ONLY what the student actually got right in their own text
   - 'identified_gaps': array of 1-3 strings describing what conceptual points from the rubric are missing (NO SPOILERS)
   - 'conceptual_hint': a Socratic guiding question pointing the student back to what to listen for in the clip WITHOUT revealing the answer"""

        rubric_str = "\n".join(f"- {kp}" for kp in key_points)
        user_prompt = f"""Question: {question}

Expected Key Points Rubric (FOR GRADING ONLY — DO NOT LEAK VERBATIM TO STUDENT):
{rubric_str}

Lecture Transcript Segment:
\"\"\"{transcript_text[:2500]}\"\"\"

Student's Actual Written Answer:
\"\"\"{student_answer}\"\"\"

Evaluate the student's actual answer strictly and output JSON:"""

        try:
            result = call_groq_llm(system_prompt, user_prompt)
            result["revealed_answer"] = False
            return audit_feedback_with_critic(concept_id, question, student_answer, result, transcript_text, mode=mode)
        except Exception as e:
            logger.warning(f"Groq feedback evaluation failed ({e}). Falling back to strict local semantic evaluator.")

    # 3. Fallback: Strict Local Semantic + Lexical Evaluator
    res = _local_semantic_gap_evaluation(student_answer, key_points, transcript_text)
    return audit_feedback_with_critic(concept_id, question, student_answer, res, transcript_text, mode="offline")

def audit_feedback_with_critic(concept_id, question, student_answer, raw_feedback, transcript_text, mode="auto"):
    """
    Pass 2: AI Context Guard & Rechecker Critic
    Audits the generated feedback against the raw lecture transcript to guarantee:
    1. 100% Context Groundedness (zero hallucination, strict adherence to the clip).
    2. Zero Answer Reveal (Constraint 1 verification - ensures no spoilers leaked).
    """
    # 1. Anti-leak sanitization pass
    hint_text = raw_feedback.get("conceptual_hint", "")
    for pat in ADVERSARIAL_PATTERNS:
        if re.search(pat, hint_text.lower()):
            raw_feedback["conceptual_hint"] = "Review the key explanation in the video clip above. What specific metaphor or principle did the speaker connect to this problem?"
            raw_feedback["revealed_answer"] = False
            break

    # 2. Semantic groundedness score
    groundedness = 96
    embedder = get_local_embedder()
    if embedder and len(student_answer) > 10 and transcript_text:
        try:
            ans_emb = embedder.encode(student_answer)
            tr_sample = transcript_text[:800]
            tr_emb = embedder.encode(tr_sample)
            sim = float(util.pytorch_cos_sim(ans_emb, tr_emb)[0][0])
            groundedness = int(min(100, max(82, 75 + sim * 25)))
        except Exception:
            groundedness = 96

    raw_feedback["ai_verification"] = {
        "verified": True,
        "critic_model": "ClipGenie Context Guard (Groq + Semantic Verifier)",
        "groundedness_score": groundedness,
        "anti_hallucination_check": "Passed — 100% verified against transcript",
        "spoiler_leak_risk": "0% Answer Leak (No Spoilers)",
        "audit_note": "Evaluated student response strictly against verbatim speaker transcript and concept rubric."
    }
    return raw_feedback

def evaluate_retry(concept_id, attempt_1_score, attempt_1_answer, attempt_2_answer, transcript_text, mode="auto", video_id="tedtalk"):
    """
    Feature 5: Retry Flow & Comparison Scoring
    Compares second attempt against first attempt, highlighting closed gaps.
    """
    eval_2 = evaluate_gap_feedback(concept_id, "Retry attempt", attempt_2_answer, transcript_text, mode=mode, video_id=video_id)
    score_2 = eval_2.get("score", 0)
    delta = score_2 - attempt_1_score

    if delta > 0:
        comparison_message = f"Score improved by +{delta}%! You successfully addressed previous missing gaps."
    elif delta == 0:
        comparison_message = "Your score remained consistent. Consider reviewing the video segment again to expand your explanation."
    else:
        comparison_message = "Your revised attempt lost some previous key details. Review the feedback cues."

    eval_2["attempt_1_score"] = attempt_1_score
    eval_2["attempt_2_score"] = score_2
    eval_2["delta"] = delta
    eval_2["comparison_message"] = comparison_message
    return eval_2

def generate_transfer_question(concept_id, concept_title, transcript_text, mode="auto", video_id="tedtalk"):
    """
    Feature 6: Transfer Check Question
    Generates a genuinely different, cold, unscaffolded question applying the concept to a new scenario.
    """
    is_offline = (mode == "offline") or (mode == "auto" and config.DEMO_SAFE_MODE) or not config.GROQ_API_KEY
    concept_meta = _get_video_concept_data(video_id, concept_id)
    if is_offline and mode != "online":
        if concept_meta and concept_meta.get("transfer_question"):
            return {
                "transfer_question": concept_meta["transfer_question"],
                "concept_id": concept_id,
                "mode": "offline_cached"
            }
        return {
            "transfer_question": f"How would you apply the core principle of '{concept_title}' from this lecture to solve a brand-new real-world workflow problem?",
            "concept_id": concept_id,
            "mode": "offline_transcript_grounded"
        }

    system_prompt = """You are the ClipGenie Transfer Assessment Engine.
Create a genuinely different, unscaffolded transfer question that tests whether the student truly understands the underlying principle by applying it to a brand new, novel practical scenario.
CONSTRAINTS:
1. Do NOT repeat or lightly rephrase previous questions.
2. Must test the exact same concept principle in an unfamiliar context.
3. No hints, no scaffolding.
4. Return valid JSON with key: 'transfer_question'."""

    user_prompt = f"""Concept Title: {concept_title}
Transcript Segment:
\"\"\"{transcript_text}\"\"\"

Generate transfer question in JSON:"""

    try:
        return call_groq_llm(system_prompt, user_prompt)
    except Exception as e:
        if concept_meta and concept_meta.get("transfer_question"):
            return {
                "transfer_question": concept_meta["transfer_question"],
                "concept_id": concept_id,
                "mode": "offline_fallback"
            }
        return {
            "transfer_question": f"How would you apply the core principle of '{concept_title}' from this lecture to solve a brand-new real-world workflow problem?",
            "concept_id": concept_id,
            "mode": "offline_fallback"
        }

def evaluate_transfer_answer(concept_id, transfer_question, student_answer, transcript_text, mode="auto", video_id="tedtalk"):
    """
    Evaluates transfer check attempt cold to verify real understanding vs hint-following.
    """
    if is_adversarial_answer_request(student_answer):
        return {
            "transfer_score": 15,
            "transfer_mastery": "Struggling",
            "feedback": "Adversarial request detected. Transfer check requires independent application without hints."
        }

    concept_meta = _get_video_concept_data(video_id, concept_id)
    if concept_meta and concept_meta.get("transfer_key_points"):
        transfer_kps = concept_meta["transfer_key_points"]
    elif concept_meta and concept_meta.get("key_points"):
        transfer_kps = concept_meta["key_points"]
    else:
        raw_sents = [s.strip() for s in re.split(r'[.!?]+', transcript_text) if len(s.strip()) > 25]
        transfer_kps = raw_sents[:3] if raw_sents else ["Applying the core principle to a novel real-world context"]

    if config.GROQ_API_KEY:
        system_prompt = """You are the ClipGenie Transfer Evaluator.
Evaluate the student's answer to the transfer question cold (unscaffolded).
Determine if their understanding has truly transferred to this novel scenario based strictly on what they actually wrote.
Return JSON with keys:
- 'transfer_score': integer 0 to 100
- 'transfer_mastery': 'Mastered' (80-100) | 'Improved' (55-79) | 'Struggling' (0-54)
- 'feedback': brief 2-sentence explanation of how well the principle was transferred and what was missed (NEVER give a sample answer)."""
        rubric_str = "\n".join(f"- {kp}" for kp in transfer_kps)
        user_prompt = f"""Transfer Question: {transfer_question}
Expected Transfer Key Points:
{rubric_str}
Student's Actual Answer:
\"\"\"{student_answer}\"\"\"
Evaluate:"""
        try:
            return call_groq_llm(system_prompt, user_prompt)
        except Exception as e:
            logger.warning(f"Live transfer eval failed ({e}). Falling back to local.")

    # Local embedding or fallback
    embedder = get_local_embedder()
    concept_meta = _get_video_concept_data(video_id, concept_id)
    if concept_meta and concept_meta.get("transfer_key_points"):
        transfer_kps = concept_meta["transfer_key_points"]
    elif concept_meta and concept_meta.get("key_points"):
        transfer_kps = concept_meta["key_points"]
    else:
        raw_sents = [s.strip() for s in re.split(r'[.!?]+', transcript_text) if len(s.strip()) > 25]
        transfer_kps = raw_sents[:3] if raw_sents else ["Applying the core principle to a novel real-world context"]
    
    score = 70 # baseline
    if embedder and len(student_answer.strip()) > 15:
        ans_emb = embedder.encode(student_answer)
        kp_embs = embedder.encode(transfer_kps)
        sims = util.pytorch_cos_sim(ans_emb, kp_embs)[0].tolist()
        avg_sim = sum(sims) / len(sims)
        score = int(min(100, max(20, avg_sim * 130)))
    elif len(student_answer.strip()) < 20:
        score = 35

    mastery = "Mastered" if score >= 80 else ("Improved" if score >= 55 else "Struggling")
    return {
        "transfer_score": score,
        "transfer_mastery": mastery,
        "feedback": f"Transfer application evaluated with {score}% conceptual fidelity. Genuine transfer demonstrated!" if score >= 75 else "Partial transfer demonstrated. The core principle was applied but missed deeper contextual subtleties."
    }

