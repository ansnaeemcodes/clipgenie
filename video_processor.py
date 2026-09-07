import whisper
import torch
from moviepy import VideoFileClip, concatenate_videoclips
import time
from sentence_transformers import SentenceTransformer, util
import os
import logging
import traceback
from storage_manager import StorageManager

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

WHISPER_MODEL_SIZE = "base"  # Can be tiny, base, small, medium, large

# Initialize storage manager
storage_mgr = StorageManager()

_whisper_model = None
_sentence_model = None

def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Loading Whisper model '{WHISPER_MODEL_SIZE}' on {device}...")
        _whisper_model = whisper.load_model(WHISPER_MODEL_SIZE, device=device)
        logger.info("Whisper model loaded successfully")
    return _whisper_model

def get_sentence_model():
    global _sentence_model
    if _sentence_model is None:
        logger.info("Loading SentenceTransformer model 'all-MiniLM-L6-v2'...")
        _sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("SentenceTransformer model loaded successfully")
    return _sentence_model

def calculate_video_duration(video_path):
    """Calculate the duration of a video file."""
    with VideoFileClip(video_path) as video_clip:
        return video_clip.duration

def format_duration(seconds):
    """Convert duration in seconds to HH:MM:SS format."""
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

def process_video(video_path, user_input, upload_folder, summarized_folder, user_id=None):
    try:
        # Generate unique filenames
        base_filename = os.path.splitext(os.path.basename(video_path))[0]
        audio_path = os.path.join(upload_folder, f"{base_filename}_audio.mp3")
        transcription_file_path = os.path.join(upload_folder, f"{base_filename}_transcription.txt")
        output_video_path = os.path.join(summarized_folder, f"{base_filename}_output.mp4")

        # Convert all paths to absolute paths
        audio_path = os.path.abspath(audio_path)
        transcription_file_path = os.path.abspath(transcription_file_path)
        output_video_path = os.path.abspath(output_video_path)

        logger.info(f"Video path: {video_path}")
        logger.info(f"Audio path: {audio_path}")
        logger.info(f"Transcription path: {transcription_file_path}")
        logger.info(f"Output path: {output_video_path}")

        # Step 1: Extract audio
        logger.info("Extracting audio from video...")
        with VideoFileClip(video_path) as video_clip:
            video_clip.audio.write_audiofile(audio_path)
        logger.info("Audio extraction completed")

        # Step 2: Load Whisper model and transcribe
        model = get_whisper_model()
        
        start = time.time()
        logger.info(f"Starting transcription of file: {audio_path}")
        result = model.transcribe(audio_path, fp16=False)
        logger.info("Transcription completed successfully")
        end = time.time()
        logger.info(f"Transcription completed in {end - start:.2f} seconds")

        # Write full transcription to file
        logger.info("Writing full transcription to file...")
        with open(transcription_file_path, 'w', encoding='utf-8') as file:
            for segment in result['segments']:
                file.write(f"{segment['start']:.2f}s {segment['end']:.2f}s {segment['text']}\n")
        logger.info(f"Full transcription saved at {transcription_file_path}")

        # Process segments
        segments = process_segments(result['segments'], user_input, video_path)

        # Create final video and save its transcript
        output_video_path = create_final_video(video_path, segments, output_video_path, summarized_folder)

        # Calculate total duration of the output video
        output_duration = calculate_video_duration(output_video_path)
        formatted_duration = format_duration(output_duration)

        # Prepare timestamps for the output video
        timestamps = [f"{segment['start']:.2f}s - {segment['end']:.2f}s" for segment in segments]
        formatted_timestamps = ", ".join(timestamps)

        # If user is logged in, move to summarized folder and upload to Firebase
        if user_id:
            storage_result = storage_mgr.process_video_storage(output_video_path, user_id)
            return {
                'local_path': output_video_path,
                'firebase_url': storage_result.get('firebase_url'),
                'duration': formatted_duration,
                'timestamps': formatted_timestamps
            }
        
        return {
            'local_path': output_video_path,
            'firebase_url': None,
            'duration': formatted_duration,
            'timestamps': formatted_timestamps
        }

    except Exception as e:
        logger.error(f"Error in process_video: {str(e)}")
        logger.error(traceback.format_exc())
        raise
    finally:
        # Cleanup temporary audio file only
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
                logger.info("Temporary audio file cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

def reconstruct_complete_sentences(whisper_segments):
    """
    Groups raw Whisper segment fragments into grammatically complete sentences.
    Ensures that clips never start or cut off mid-sentence.
    """
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

        # If there's a long silence (> 1.6s) between segments, treat as a natural boundary
        is_long_silence = (last_seg_end is not None and (seg_start - last_seg_end) > 1.6)

        if current_start is None:
            current_start = seg_start
        current_end = seg_end
        current_text = (current_text + " " + text).strip()
        last_seg_end = seg_end

        # Check if text ends with sentence-ending punctuation
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

def extract_coherent_thought_blocks(sentences, user_input, min_clip_duration=18.0, max_clip_duration=60.0, top_k=5):
    """
    Finds the most relevant complete sentences based on the user prompt, then expands
    them backwards and forwards to form a complete, coherent narrative thought block
    composed strictly of complete sentences.
    """
    if not sentences:
        return []

    logger.info("Generating embeddings for complete sentences...")
    model_sentence = get_sentence_model()
    sentences_text = [s['text'] for s in sentences]
    embeddings = model_sentence.encode(sentences_text)

    logger.info(f"Calculating similarity scores for prompt: '{user_input}'")
    query_embedding = model_sentence.encode([user_input])
    similarity_scores = util.pytorch_cos_sim(query_embedding, embeddings)[0].tolist()

    for idx, s in enumerate(sentences):
        s['score'] = similarity_scores[idx]
        s['idx'] = idx

    # Sort sentences by semantic similarity
    scored_sentences = sorted(sentences, key=lambda s: s['score'], reverse=True)

    candidate_blocks = []

    for target in scored_sentences[:top_k]:
        target_idx = target['idx']
        start_idx = target_idx
        end_idx = target_idx

        # Expand backwards (setup/premise) and forwards (conclusion/punchline)
        while True:
            curr_dur = sentences[end_idx]['end'] - sentences[start_idx]['start']
            if curr_dur >= min_clip_duration:
                break

            can_expand_back = start_idx > 0
            can_expand_fwd = end_idx < len(sentences) - 1

            if not can_expand_back and not can_expand_fwd:
                break

            # Symmetrically expand: forward first, then backward
            if can_expand_fwd and (not can_expand_back or (end_idx - target_idx <= target_idx - start_idx)):
                next_dur = sentences[end_idx + 1]['end'] - sentences[start_idx]['start']
                if next_dur > max_clip_duration and curr_dur >= 12.0:
                    break
                end_idx += 1
            elif can_expand_back:
                next_dur = sentences[end_idx]['end'] - sentences[start_idx - 1]['start']
                if next_dur > max_clip_duration and curr_dur >= 12.0:
                    break
                start_idx -= 1

        block_text = " ".join([sentences[k]['text'] for k in range(start_idx, end_idx + 1)])
        candidate_blocks.append({
            'start_idx': start_idx,
            'end_idx': end_idx,
            'start': sentences[start_idx]['start'],
            'end': sentences[end_idx]['end'],
            'text': block_text,
            'score': max([sentences[k]['score'] for k in range(start_idx, end_idx + 1)])
        })

    # Sort by relevance and eliminate overlapping blocks
    candidate_blocks.sort(key=lambda b: b['score'], reverse=True)
    chosen_blocks = []
    for block in candidate_blocks:
        overlap = False
        for chosen in chosen_blocks:
            if not (block['end'] <= chosen['start'] or block['start'] >= chosen['end']):
                overlap = True
                break
        if not overlap:
            chosen_blocks.append(block)

    # Sort chosen blocks chronologically
    chosen_blocks.sort(key=lambda b: b['start'])
    return chosen_blocks

def merge_and_pad_blocks(blocks, sentences, video_duration, close_gap=8.0, max_total_duration=360.0):
    """
    Merges nearby blocks by connecting intermediate complete sentences if gap <= close_gap,
    and applies subtle audio onset/offset padding so speech is never abruptly chopped.
    """
    if not blocks:
        return []

    merged = []
    current_block = blocks[0]

    for next_block in blocks[1:]:
        gap = next_block['start'] - current_block['end']
        if gap <= close_gap:
            # Connect them using complete sentences in between
            start_idx = current_block['start_idx']
            end_idx = next_block['end_idx']
            merged_text = " ".join([sentences[k]['text'] for k in range(start_idx, end_idx + 1)])
            current_block = {
                'start_idx': start_idx,
                'end_idx': end_idx,
                'start': sentences[start_idx]['start'],
                'end': sentences[end_idx]['end'],
                'text': merged_text,
                'score': max(current_block['score'], next_block['score'])
            }
        else:
            merged.append(current_block)
            current_block = next_block

    merged.append(current_block)

    # Apply audio padding and total video duration cap
    final_segments = []
    total_duration = 0.0

    for b in merged:
        # Subtle audio boundary padding (0.15s start, 0.25s end) to protect spoken syllables
        padded_start = max(0.0, b['start'] - 0.15)
        padded_end = min(video_duration, b['end'] + 0.25)
        seg_duration = padded_end - padded_start

        if total_duration + seg_duration > max_total_duration and total_duration > 30.0:
            break

        final_segments.append({
            'start': padded_start,
            'end': padded_end,
            'text': b['text']
        })
        total_duration += seg_duration

    return final_segments

def process_segments(raw_segments, user_input, video_path):
    with VideoFileClip(video_path) as video_clip:
        video_duration = video_clip.duration

    # 1. Reconstruct raw Whisper fragments into complete sentences
    sentences = reconstruct_complete_sentences(raw_segments)
    logger.info(f"Reconstructed {len(sentences)} complete sentences from {len(raw_segments)} raw whisper fragments.")

    if not sentences:
        logger.warning("No sentences could be reconstructed; falling back to raw segments.")
        return raw_segments[:5]

    # 2. Extract coherent thought blocks around the user's focus prompt
    thought_blocks = extract_coherent_thought_blocks(sentences, user_input)
    logger.info(f"Selected {len(thought_blocks)} coherent thought blocks for prompt '{user_input}'.")

    # 3. Merge close gaps and apply natural audio boundary padding
    final_segments = merge_and_pad_blocks(thought_blocks, sentences, video_duration)
    logger.info(f"Final output video composed of {len(final_segments)} continuous, complete sentence clips.")

    return final_segments

def create_final_video(video_path, segments, output_video_path, summarized_folder):
    logger.info("Creating final video...")
    video_segments = []

    output_transcription_file_path = os.path.join(summarized_folder, f"{os.path.basename(output_video_path)}_transcription.txt")

    with VideoFileClip(video_path) as video_clip:
        video_duration = video_clip.duration

        with open(output_transcription_file_path, 'w', encoding='utf-8') as file:
            for segment in segments:
                try:
                    start_time = segment["start"]
                    end_time = min(segment["end"], video_duration)

                    if start_time >= video_duration:
                        logger.warning(f"Skipping segment {start_time}s - {end_time}s (out of bounds)")
                        continue

                    logger.info(f"Extracting complete sentence clip from {start_time:.2f}s to {end_time:.2f}s")
                    video_segment = video_clip.subclipped(start_time, end_time)
                    video_segments.append(video_segment)

                    # Write output transcript with complete sentence text
                    file.write(f"{start_time:.2f}s {end_time:.2f}s {segment['text']}\n")

                except Exception as e:
                    logger.error(f"Error extracting segment {segment}: {str(e)}")
                    logger.error(traceback.format_exc())

        if video_segments:
            logger.info(f"Combining {len(video_segments)} video segments...")
            final_video = concatenate_videoclips(video_segments, method="chain")

            start = time.time()
            final_video.write_videofile(
                output_video_path,
                codec="libx264",
                audio_codec="aac",
                fps=30,
                bitrate="1670k",
                threads=0,
                preset="ultrafast"
            )
            end = time.time()
            logger.info(f"Video export completed in {end - start:.2f} seconds")

            # Clean up video segments
            for segment in video_segments:
                segment.close()
            final_video.close()
        else:
            logger.warning("No video segments to combine")

    return output_video_path