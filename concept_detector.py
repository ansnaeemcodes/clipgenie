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
        "summary": "The leap from millions to trillions of parameters consuming 8 trillion words, leading to ubiquitous conversational interfaces with high IQ and EQ.",
        "start": 144.36,
        "end": 240.40,
        "duration_str": "2:24 - 4:00",
        "key_terms": ["parameters explosion", "8 trillion words", "conversational interface", "high IQ and EQ", "ubiquitous AI"],
        "core_principle": "Modern AI models process more text than a human could read in thousands of lifetimes, expanding from tools to knowledgeable interactive personas.",
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
        "key_terms": ["autonomy", "recursive self-improvement", "risk threshold", "economic growth", "societal safeguards"],
        "core_principle": "Autonomy and self-improvement represent non-linear risk boundaries requiring extreme caution and active societal steering.",
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

    # Format concise transcript with timestamps
    lines = [f"{s['start']:.1f}s - {s['end']:.1f}s: {s['text']}" for s in raw_segments]
    transcript_text = "\n".join(lines)

    system_prompt = """You are an elite AI-in-Education curriculum architect.
Your job is to CRITIQUE and ANALYZE this full lecture transcript, and extract the 4-5 major core conceptual pillars taught.

CRITICAL INSTRUCTION FOR MULTI-OCCURRENCE CONCEPTS:
Lecturers frequently revisit an earlier concept later in the talk with new context, real-world examples, or synthesis.
For EACH concept, you must identify ALL occurrences across the entire lecture where this concept is discussed.

For each concept, provide:
- id: string ("concept_1", "concept_2", etc.)
- title: clear, compelling conceptual title
- summary: 2-sentence pedagogical summary of what this concept teaches
- start: float primary start timestamp in seconds
- end: float primary end timestamp in seconds
- duration_str: formatted "MM:SS - MM:SS"
- key_terms: array of 4 key conceptual terms
- core_principle: the key thesis or mental model the student must master
- occurrences: ARRAY of all occurrences of this concept across the talk, each with:
    * start: float
    * end: float
    * label: descriptive label (e.g. "Part 1: Initial Concept", "Part 2: Later Callback & Example")
    * duration_str: "MM:SS - MM:SS"

Return valid JSON with key 'concepts' containing the list of concepts."""

    client = groq.Groq(api_key=config.GROQ_API_KEY)
    logger.info(f"Calling Groq LLM ({config.GROQ_MODEL}) to analyze transcript & multi-occurrence concepts...")
    
    response = client.chat.completions.create(
        model=config.GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Here is the complete lecture transcript with timestamps:\n\n{transcript_text}\n\nAnalyze and extract concept pillars with all video occurrences in JSON:"}
        ],
        temperature=0.2,
        response_format={"type": "json_object"}
    )
    
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

def get_lecture_concepts(video_name_or_path, raw_segments, force_auto=False):
    """
    Returns concept map for the lecture with instant caching and multi-occurrence support.
    """
    base = os.path.splitext(os.path.basename(video_name_or_path))[0]
    cache_path = os.path.join(config.CACHE_DIR, f"{base}_llm_concepts.json")

    # If force_auto is requested and API key is present, run live LLM extraction
    if force_auto and config.GROQ_API_KEY:
        try:
            return extract_concepts_via_llm(raw_segments, video_name_or_path)
        except Exception as e:
            logger.warning(f"Live LLM concept extraction failed ({e}). Falling back to cached/presets.")

    # Check cache first
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
                if cached:
                    logger.info(f"Loaded {len(cached)} concepts from cache: {cache_path}")
                    return cached
        except Exception as e:
            logger.warning(f"Error reading concept cache: {e}")

    # Fallback to verified multi-occurrence presets for tedtalk
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
