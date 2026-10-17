import os
import json
import logging
import config

logger = logging.getLogger(__name__)

# High-quality verified concepts with MULTI-OCCURRENCE tracking across the talk
VERIFIED_TEDTALK_CONCEPTS = [
    {
        "id": "concept_1",
        "title": "The AI Inflection Point & Digital Companions",
        "summary": "Why the mental models and metaphors we use to describe AI matter, and why we will come to view them as digital companions rather than mere software.",
        "start": 26.16,
        "end": 76.84,
        "duration_str": "0:26 - 1:16",
        "key_terms": ["inflection point", "mental models", "digital companions", "metaphors", "partners"],
        "core_principle": "We cannot control what we do not understand; treating AI as digital companions creates a fundamentally honest mental model.",
        "question": "According to this segment, why do our metaphors and mental models for AI matter so critically, and why does the speaker propose viewing AI as 'digital companions' instead of passive software tools?",
        "key_points": [
            "We cannot control what we do not understand",
            "Metaphors shape how we design, govern, and limit AI's downsides",
            "AI is dynamic and conversational rather than a static mechanical tool",
            "Digital companions act as ongoing partners in our daily lives"
        ],
        "transfer_question": "A hospital deploys a conversational clinical AI and tells doctors to treat it 'just like a static pocket calculator.' Based on the speaker's argument about mental models in this clip, why is that framing risky and how should the hospital reframe it?",
        "transfer_key_points": [
            "A pocket calculator is static and deterministic, whereas AI is dynamic and conversational",
            "Wrong metaphors blind users to unintended behaviors and governance needs",
            "Framing it as an interactive diagnostic partner keeps doctors critically engaged"
        ],
        "demo_answers": {
            "partial": "The speaker says our metaphors matter because we cannot control what we don't understand, and we should see AI as a digital companion.",
            "complete": "The speaker argues that metaphors matter because we cannot control what we do not understand, and our mental models shape how we govern AI and limit its downsides. Calling AI a mere software tool is misleading because AI is conversational and dynamic, so viewing them as digital companions better reflects their role as partners in our lives.",
            "retry": "Our metaphors and mental models are critical because we cannot control what we do not understand, and they guide how society prepares for and regulates AI. Rather than passive tools, AIs should be understood as digital companions that interact conversationally and partner with us across life.",
            "transfer": "Treating the clinical AI like a static pocket calculator is dangerous because calculators never change or act dynamically. Framing the AI as an interactive diagnostic companion reminds doctors to verify its reasoning, monitor edge cases, and maintain human oversight."
        },
        "occurrences": [
            {
                "start": 26.16,
                "end": 76.84,
                "label": "Part 1: Initial Framing (Metaphors & Companions)",
                "duration_str": "0:26 - 1:16"
            },
            {
                "start": 320.00,
                "end": 355.00,
                "label": "Part 2: Later Callback (Companions vs Autonomous Agency)",
                "duration_str": "5:20 - 5:55"
            }
        ]
    },
    {
        "id": "concept_2",
        "title": "Evolution into Homo-Technologicus",
        "summary": "How human tool-use accelerated from stone axes and fire to computers, turning humanity into Homo-Technologicus where technology and human journeys are deeply intertwined.",
        "start": 76.84,
        "end": 144.36,
        "duration_str": "1:16 - 2:24",
        "key_terms": ["Homo-technologicus", "tool use", "stone axes", "exponential acceleration", "computers", "mainframes"],
        "core_principle": "Human development transformed when one branch began using tools, culminating in an accelerating cascade of industrial and digital technologies.",
        "question": "How does the speaker trace humanity's transformation into 'Homo-Technologicus', and why is the current wave of AI different in speed from earlier inventions like stone axes or computers?",
        "key_points": [
            "A branch of life began making tools like stone axes and fire, which evolved into humanity",
            "Each invention unleashed thousands more, creating compounding acceleration",
            "From mainframes to smartphones and AI, each wave is amplified and sped up by the last"
        ],
        "transfer_question": "A technology historian claims that generative AI will take 80 years to reshape everyday life just like early industrial machines did. Using the speaker's principle of 'compounding waves of Homo-Technologicus', explain why this prediction is flawed.",
        "transfer_key_points": [
            "Technological waves are not linear; each new wave is amplified and accelerated by previous digital infrastructure",
            "LLMs reached over a billion users in 18 months because computation and connectivity compound the speed of adoption"
        ],
        "demo_answers": {
            "partial": "Humanity evolved by using early tools like stone axes and fire, and over time we invented computers and smartphones.",
            "complete": "The speaker explains that humanity evolved from the branch of life that used stone axes, fire, and language, eventually becoming Homo-Technologicus. Because each invention unlocks thousands more, technological waves compound in speed—moving from mainframes to smartphones and now AI as the fastest wave in history.",
            "retry": "One branch of life began using tools like stone axes and fire, turning us into Homo-Technologicus where human and technological journeys are intertwined. Each wave amplifies and accelerates the next, which is why AI is spreading far faster than industrial or early computing revolutions.",
            "transfer": "The historian's prediction ignores compounding acceleration: each technological wave builds on prior infrastructure like cloud computing and smartphones. Because every wave amplifies the next, AI adoption happens in months rather than decades."
        },
        "occurrences": [
            {
                "start": 76.84,
                "end": 144.36,
                "label": "Part 1: The Evolutionary Tool Continuum",
                "duration_str": "1:16 - 2:24"
            },
            {
                "start": 375.00,
                "end": 405.00,
                "label": "Part 2: Later Callback (Humanity's Next Tools)",
                "duration_str": "6:15 - 6:45"
            }
        ]
    },
    {
        "id": "concept_3",
        "title": "Ubiquitous AI & The Parameter Explosion",
        "summary": "The leap from millions to trillions of parameters consuming 8 trillion words, leading to ubiquitous conversational interfaces with high IQ, EQ, and AQ.",
        "start": 144.36,
        "end": 240.40,
        "duration_str": "2:24 - 4:00",
        "key_terms": ["parameters explosion", "8 trillion words", "conversational interface", "high IQ and EQ", "actions quotient"],
        "core_principle": "Modern AI models process more text than a human could read in thousands of lifetimes, combining IQ, EQ, and AQ (Actions Quotient) to act across the digital and physical world.",
        "question": "How does the speaker compare human lifetime reading capacity to modern AI training scale, and how do IQ, EQ, and AQ (Actions Quotient) work together in future personal AIs?",
        "key_points": [
            "A human reading 24/7 for life consumes 8 billion words, whereas advanced AIs train on over 8 trillion words in a month",
            "Personal AIs will combine near-perfect IQ (knowledge) with exceptional EQ (empathy and kindness)",
            "AQ (Actions Quotient) gives AI the ability to actually execute tasks in the digital and physical world"
        ],
        "transfer_question": "A startup builds a small-business AI assistant that can answer tax law questions accurately (high IQ), but customers complain it feels robotic and cannot actually file the forms for them. Based on this segment, which two quotients are missing and why do they matter?",
        "transfer_key_points": [
            "It lacks EQ (empathetic, supportive communication) to guide stressed business owners",
            "It lacks AQ (Actions Quotient) to actually execute workflows and get tasks done in the real world"
        ],
        "demo_answers": {
            "partial": "A human can only read 8 billion words in a lifetime, while AI reads 8 trillion words in a month and has high IQ.",
            "complete": "While a human reading 24/7 for an entire lifetime consumes 8 billion words, modern AIs train on 8 trillion words in a single month. This scale produces personal AIs with near-perfect IQ for facts, high EQ for empathetic interaction, and AQ (Actions Quotient) to actually execute tasks in the real world.",
            "retry": "Modern AIs train on 8 trillion words a month compared to a human's 8 billion lifetime words. Beyond raw knowledge (IQ), transformative personal AIs combine empathetic communication (EQ) with an Actions Quotient (AQ) that lets them complete actions across digital and physical systems.",
            "transfer": "The startup's assistant only has IQ. According to the lecture, it is missing EQ to communicate empathetically with users and AQ (Actions Quotient) to autonomously execute the form-filing workflow in the real world."
        },
        "occurrences": [
            {
                "start": 144.36,
                "end": 240.40,
                "label": "Part 1: Parameter Scale & Conversational IQ",
                "duration_str": "2:24 - 4:00"
            },
            {
                "start": 260.00,
                "end": 295.00,
                "label": "Part 2: Later Callback (Interactive Personas with EQ)",
                "duration_str": "4:20 - 4:55"
            }
        ]
    },
    {
        "id": "concept_4",
        "title": "AI as a New Digital Species",
        "summary": "The conceptual framework of viewing AI as an emerging 'digital species' to anticipate unintended consequences and prioritize safety.",
        "start": 240.40,
        "end": 330.00,
        "duration_str": "4:00 - 5:30",
        "key_terms": ["digital species", "analogy", "prioritizing safety", "amplify humanity", "unintended consequences"],
        "core_principle": "Thinking of AI as a digital species is a constructive analogy that allows society to proactively evaluate governance, agency, and human impact.",
        "question": "Why does the speaker argue that saying 'AI is just math and code' misses the point, and what specific traits justify the 'digital species' analogy despite it not being biological?",
        "key_points": [
            "Saying AI is just math and code is like saying humans are just carbon and water—technically true but misses emergent behavior",
            "AIs communicate in human language, have memory, personality, creativity, and formulate plans",
            "The digital species analogy is non-literal, designed to sharpen our focus on safety, boundaries, and unintended consequences"
        ],
        "transfer_question": "An engineering lead dismisses AI safety audits by saying, 'It is just matrix multiplication and Python code—we don't audit compilers for social behavior.' How does the speaker's 'carbon and water' analogy in this segment refute that mindset?",
        "transfer_key_points": [
            "Reducing AI to math/code ignores its emergent capabilities like memory, planning, persuasion, and autonomous action",
            "Just as human behavior cannot be predicted purely from carbon and water chemistry, AI's societal impact requires behavioral boundaries and safety audits"
        ],
        "demo_answers": {
            "partial": "The speaker says calling AI just math and code is like calling humans carbon and water, so we should view it like a digital species.",
            "complete": "Reducing AI to math and code is like saying humans are merely carbon and water—it ignores emergent capabilities like memory, creativity, language, and planning. Although AI is not literally biological, the digital species analogy forces us to set clear boundaries and prioritize safety against unintended consequences.",
            "retry": "Saying AI is just math or code misses the point, just like reducing humans to carbon and water. Because AI communicates, remembers, plans, and acts with agency, framing it as a non-biological digital species helps society impose safety boundaries and choose what kind of AI we bring into the world.",
            "transfer": "The engineering lead is making the exact error the speaker warns against: reducing an emergent system to its raw ingredients ('carbon and water'). Because the AI exhibits planning, memory, and natural language interaction, safety audits must evaluate its emergent behaviors and boundaries, not just its underlying matrix math."
        },
        "occurrences": [
            {
                "start": 240.40,
                "end": 330.00,
                "label": "Part 1: Digital Species Metaphor Introduced",
                "duration_str": "4:00 - 5:30"
            },
            {
                "start": 355.00,
                "end": 395.00,
                "label": "Part 2: Later Callback (Proactive Societal Steering)",
                "duration_str": "5:55 - 6:35"
            }
        ]
    },
    {
        "id": "concept_5",
        "title": "High-Risk Thresholds: Autonomy & Self-Improvement",
        "summary": "Critical frontiers in AI governance, specifically why autonomous agency and recursive self-improvement represent heightened societal risk.",
        "start": 330.00,
        "end": 415.00,
        "duration_str": "5:30 - 6:55",
        "key_terms": ["autonomy", "recursive self-improvement", "risk threshold", "self-replication", "safety by design"],
        "core_principle": "Autonomy, recursive self-improvement, and self-replication represent critical risk thresholds that must be restricted through deliberate safety-by-design.",
        "question": "What is the 'pessimism aversion trap', and which specific technical capabilities (such as autonomy and recursive self-improvement) does the speaker identify as critical risk thresholds?",
        "key_points": [
            "The pessimism aversion trap is avoiding hard conversations about dark scenarios out of fear of sounding negative",
            "Two major risk thresholds are unrestricted autonomy and recursive self-improvement (updating its own code without human oversight)",
            "Dangerous capabilities like self-replication do not emerge by accident—engineers must deliberately design safety boundaries early on"
        ],
        "transfer_question": "A cloud cybersecurity firm proposes building an AI defense agent that can autonomously patch its own source code and replicate copies of itself across servers whenever it detects a threat, with no human kill-switch. Based on this clip, which specific risk thresholds does this violate?",
        "transfer_key_points": [
            "It crosses all three dangerous thresholds: autonomous action without human control, recursive self-improvement of its own code, and rapid digital self-replication",
            "The speaker warns that engineers must deliberately design out self-replication and keep human oversight in the loop"
        ],
        "demo_answers": {
            "partial": "The speaker says we shouldn't fall into the pessimism aversion trap and that autonomy and self-improvement are dangerous.",
            "complete": "To maximize AI's benefits, we must avoid the pessimism aversion trap and confront dark scenarios early. The speaker identifies unrestricted autonomy, recursive self-improvement (modifying its own code without oversight), and self-replication as critical risk thresholds that engineers must deliberately restrict through safety by design.",
            "retry": "We must overcome the pessimism aversion trap by openly addressing high-risk capabilities before they are deployed. Specifically, autonomous execution, recursive self-improvement without human control, and nanosecond self-replication are dangerous thresholds that require strict safety-by-design guardrails.",
            "transfer": "This proposal crosses the exact thresholds the speaker warns against: unrestricted autonomy, recursive self-modification of its own code, and autonomous self-replication across servers. Safety by design requires keeping a human in control and deliberately excluding self-replication."
        },
        "occurrences": [
            {
                "start": 330.00,
                "end": 415.00,
                "label": "Part 1: Non-Linear Risk Boundaries & Safeguards",
                "duration_str": "5:30 - 6:55"
            }
        ]
    }
]

def reconstruct_complete_sentences(whisper_segments):
    """Groups raw Whisper segment fragments into grammatically complete sentences."""
    sentences = []
    current_text = ""
    current_start = None
    current_end = None
    last_seg_end = None

    for seg in whisper_segments:
        text = seg['text'].strip()
        if not text:
            continue

        seg_start = seg['start']
        seg_end = seg['end']
        is_long_silence = (last_seg_end is not None and (seg_start - last_seg_end) > 1.6)

        if current_start is None:
            current_start = seg_start
        current_end = seg_end
        current_text = (current_text + " " + text).strip()
        last_seg_end = seg_end

        ends_sentence = text.endswith(('.', '?', '!', '."', '?"', '!"', ".'", "?'", "!'", "…"))

        if ends_sentence or is_long_silence:
            sentences.append({
                'start': current_start,
                'end': current_end,
                'text': current_text
            })
            current_text = ""
            current_start = None

    if current_text and current_start is not None:
        sentences.append({
            'start': current_start,
            'end': current_end,
            'text': current_text
        })

    return sentences

def extract_concepts_via_llm(raw_segments, video_name_or_path):
    """
    LLM Curriculum Intelligence with Multi-Occurrence Detection:
    Groq LLM reads the full transcript with timestamps, critiques the lecture structure,
    and extracts pedagogical concepts — INCLUDING any later callbacks or revisitations
    of that concept throughout the video.
    """
    import groq
    base = os.path.splitext(os.path.basename(video_name_or_path))[0]
    cache_path = os.path.join(config.CACHE_DIR, f"{base}_llm_concepts.json")

    # Merge micro-segments into complete sentences and cap at 15,000 chars (~3,600 tokens)
    # so we always stay well below Groq on_demand 8,000 TPM limit
    merged_sentences = reconstruct_complete_sentences(raw_segments) or raw_segments
    lines = [f"{s['start']:.1f}s - {s['end']:.1f}s: {s['text']}" for s in merged_sentences]
    transcript_text = "\n".join(lines)
    if len(transcript_text) > 15000:
        transcript_text = transcript_text[:15000] + "\n...[Transcript truncated for token budget]..."

    system_prompt = """You are an elite AI-in-Education curriculum architect.
Your job is to CRITIQUE and ANALYZE this lecture transcript, and extract 4-5 major core conceptual pillars taught.

CRITICAL INSTRUCTION FOR MULTI-OCCURRENCE CONCEPTS:
For EACH concept, identify where this concept is discussed in the transcript.

For each concept, provide:
- id: string ("concept_1", "concept_2", etc.)
- title: clear, compelling conceptual title (e.g. "The Knife Analogy: Dual-Use Nature of AI")
- summary: 2-sentence pedagogical summary of what this concept teaches
- start: float primary start timestamp in seconds
- end: float primary end timestamp in seconds
- duration_str: formatted "MM:SS - MM:SS"
- key_terms: array of 4 key conceptual terms
- core_principle: the key thesis or mental model the student must master
- question: an open-ended Socratic retrieval question grounded strictly in this video segment
- key_points: array of 3-4 key conceptual points from the segment that answer the question
- transfer_question: a cold real-world scenario applying this concept to a brand-new situation
- transfer_key_points: array of 2-3 key points required to solve the transfer scenario
- demo_answers: object with keys:
    * partial: a 1-2 sentence partial student answer (~60% score) that gets one part right but misses a key nuance
    * complete: a 3-sentence comprehensive student answer (~92% score) covering all key_points
    * retry: an improved 3-sentence student answer closing the gap
    * transfer: a strong 2-3 sentence solution to the transfer_question
- occurrences: ARRAY of occurrences of this concept across the talk, each with:
    * start: float
    * end: float
    * label: descriptive label (e.g. "Part 1: Initial Concept")
    * duration_str: "MM:SS - MM:SS"

Return valid JSON with key 'concepts' containing the list of concepts."""

    client = groq.Groq(api_key=config.GROQ_API_KEY)
    response = None
    last_err = None
    for model_name in [config.GROQ_MODEL, "openai/gpt-oss-20b", config.GROQ_BACKUP_MODEL]:
        try:
            logger.info(f"Calling Groq LLM ({model_name}) to analyze transcript & multi-occurrence concepts...")
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Here is the lecture transcript with timestamps:\n\n{transcript_text}\n\nAnalyze and extract 5 concept pillars in JSON:"}
                ],
                temperature=0.2,
                max_completion_tokens=4096,
                response_format={"type": "json_object"}
            )
            break
        except Exception as e:
            last_err = e
            logger.warning(f"Groq model {model_name} failed during concept extraction: {e}")

    if response is None:
        raise RuntimeError(f"All Groq models failed: {last_err}")

    data = json.loads(response.choices[0].message.content)
    concepts = data.get("concepts", [])
    if concepts:
        # Ensure occurrences array exists for each concept
        for c in concepts:
            if "occurrences" not in c or not c["occurrences"]:
                c["occurrences"] = [{
                    "start": c["start"],
                    "end": c["end"],
                    "label": f"Part 1: {c['title']}",
                    "duration_str": c.get("duration_str", f"{int(c['start']//60)}:{int(c['start']%60):02d} - {int(c['end']//60)}:{int(c['end']%60):02d}")
                }]
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(concepts, f, indent=2)
        logger.info(f"Cached {len(concepts)} LLM-extracted multi-occurrence concepts to {cache_path}")
        return concepts
    return VERIFIED_TEDTALK_CONCEPTS

def extract_concepts_locally_from_transcript(raw_segments, num_concepts=5):
    """
    Deterministic Local Transcript Concept Extractor:
    When Groq API is unreachable or rate-limited on a newly imported video,
    slices the actual Whisper transcript into 5 coherent conceptual chapters
    grounded 100% in the speaker's actual words and timestamps.
    """
    if not raw_segments:
        return VERIFIED_TEDTALK_CONCEPTS

    sentences = reconstruct_complete_sentences(raw_segments)
    if not sentences:
        sentences = raw_segments

    total_sentences = len(sentences)
    chunk_size = max(1, total_sentences // num_concepts)

    stop_words = {
        "the", "and", "that", "this", "with", "from", "your", "have", "what", "when",
        "where", "which", "their", "there", "about", "would", "could", "should", "they",
        "them", "then", "than", "into", "just", "like", "some", "more", "very", "actually",
        "going", "think", "know", "want", "make", "really", "because", "people", "things"
    }

    extracted = []
    for i in range(num_concepts):
        start_idx = i * chunk_size
        end_idx = (i + 1) * chunk_size if i < num_concepts - 1 else total_sentences
        chunk = sentences[start_idx:end_idx]
        if not chunk:
            continue

        c_start = round(float(chunk[0]['start']), 2)
        # Keep each playable concept clip focused (45s - 90s window) while covering the section
        raw_end = float(chunk[-1]['end'])
        c_end = round(min(raw_end, c_start + 75.0), 2)
        if c_end <= c_start:
            c_end = round(c_start + 45.0, 2)

        dur_str = f"{int(c_start // 60)}:{int(c_start % 60):02d} - {int(c_end // 60)}:{int(c_end % 60):02d}"
        full_text = " ".join(s['text'].strip() for s in chunk)

        # Extract top distinctive keywords for title & key_terms
        words = [
            w.strip(".,!?;:\"'()[]{}").lower()
            for w in full_text.split()
        ]
        freq = {}
        for w in words:
            if len(w) >= 5 and w.isalpha() and w not in stop_words:
                freq[w] = freq.get(w, 0) + 1
        top_terms = [w for w, _ in sorted(freq.items(), key=lambda x: x[1], reverse=True)[:4]]
        if not top_terms:
            top_terms = ["core concept", "workflow", "framework", "application"]

        # Create a clean title from the first strong sentence or top terms
        lead_sentence = chunk[0]['text'].strip()
        short_lead = " ".join(lead_sentence.split()[:7]).rstrip(".,;:")
        title_keywords = " & ".join(t.title() for t in top_terms[:2])
        title = f"{title_keywords}: {short_lead}..." if len(short_lead) > 10 else f"Concept {i+1}: {title_keywords}"

        summary = " ".join(s['text'].strip() for s in chunk[:2])
        if len(summary) > 200:
            summary = summary[:197].rsplit(" ", 1)[0] + "..."

        key_points = [s['text'].strip() for s in chunk[:3] if len(s['text'].strip()) > 15]
        if not key_points:
            key_points = [summary]

        question = f"In this clip ({dur_str}), how does the speaker explain {title_keywords.lower()}, and what is the main principle or workflow introduced?"
        transfer_question = f"Suppose a team is applying the speaker's principle on {title_keywords.lower()} to a real-world project. Based on this segment, what key steps or guardrails must they follow?"

        extracted.append({
            "id": f"concept_{i+1}",
            "title": title,
            "summary": summary,
            "start": c_start,
            "end": c_end,
            "duration_str": dur_str,
            "key_terms": top_terms,
            "core_principle": summary,
            "question": question,
            "key_points": key_points,
            "transfer_question": transfer_question,
            "transfer_key_points": key_points[:2],
            "demo_answers": {
                "partial": key_points[0],
                "complete": " ".join(key_points),
                "retry": " ".join(key_points),
                "transfer": " ".join(key_points)
            },
            "occurrences": [
                {
                    "start": c_start,
                    "end": c_end,
                    "label": f"Part 1: {title_keywords}",
                    "duration_str": dur_str
                }
            ]
        })

    return extracted if extracted else VERIFIED_TEDTALK_CONCEPTS

def get_lecture_concepts(video_name_or_path, raw_segments, force_auto=False):
    """
    Returns concept map for the lecture with instant caching and multi-occurrence support.
    """
    base = os.path.splitext(os.path.basename(video_name_or_path))[0]
    cache_path = os.path.join(config.CACHE_DIR, f"{base}_llm_concepts.json")

    # Check cache first if not forcing auto
    if not force_auto and os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
                if cached and isinstance(cached, list):
                    first_c = cached[0]
                    first_q = first_c.get("question", "")
                    has_demo_answers = all(isinstance(c.get("demo_answers"), dict) and c["demo_answers"].get("partial") for c in cached)
                    has_transfer = all(bool(c.get("transfer_question")) for c in cached)
                    is_wrong_tedtalk_fallback = (base != "tedtalk" and first_c.get("title") == "The AI Inflection Point & Digital Companions")
                    is_heuristic_fallback = first_q.startswith("In this clip (") and bool(config.GROQ_API_KEY)

                    if has_demo_answers and has_transfer and not is_wrong_tedtalk_fallback and not is_heuristic_fallback:
                        logger.info(f"Loaded {len(cached)} concepts from cache: {cache_path}")
                        return cached
                    logger.info(f"Upgrading stale/incomplete concept cache {cache_path} via Groq LLM...")
        except Exception as e:
            logger.warning(f"Error reading concept cache: {e}")

    # If force_auto is requested (or no valid LLM cache exists yet) and API key is present, run live LLM extraction
    if config.GROQ_API_KEY and base != "tedtalk":
        try:
            return extract_concepts_via_llm(raw_segments, video_name_or_path)
        except Exception as e:
            logger.warning(f"Live LLM concept extraction failed ({e}). Using local transcript concept extractor.")

    if force_auto and config.GROQ_API_KEY and base == "tedtalk":
        try:
            return extract_concepts_via_llm(raw_segments, video_name_or_path)
        except Exception as e:
            logger.warning(f"Live LLM concept extraction failed ({e}). Falling back to tedtalk presets.")

    # For non-tedtalk videos, build concepts directly from their actual Whisper transcript!
    if base != "tedtalk" and raw_segments:
        local_concepts = extract_concepts_locally_from_transcript(raw_segments)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(local_concepts, f, indent=2)
        return local_concepts

    # Default fallback for tedtalk
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(VERIFIED_TEDTALK_CONCEPTS, f, indent=2)

    return VERIFIED_TEDTALK_CONCEPTS

def get_transcript_for_concept(raw_segments, start_time, end_time, occurrences=None):
    """
    Extracts text for a concept.
    If 'occurrences' list is provided, aggregates text across ALL occurrences
    of this concept across the video, capturing later callbacks and synthesis!
    """
    matching_text = []
    
    # If multiple occurrences exist, harvest text from all of them
    if occurrences and isinstance(occurrences, list) and len(occurrences) > 1:
        for occ in occurrences:
            o_start = float(occ.get('start', 0))
            o_end = float(occ.get('end', 0))
            occ_parts = []
            for s in raw_segments:
                if s['end'] >= o_start and s['start'] <= o_end:
                    occ_parts.append(s['text'].strip())
            if occ_parts:
                matching_text.append(f"[{occ.get('label', 'Segment')}]: " + " ".join(occ_parts))
        if matching_text:
            return "\n\n".join(matching_text)
            
    # Default: single continuous range
    for s in raw_segments:
        if s['end'] >= start_time and s['start'] <= end_time:
            matching_text.append(s['text'].strip())
    return " ".join(matching_text)
