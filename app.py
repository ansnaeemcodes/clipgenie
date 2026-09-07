import os
import json
import shutil
from flask import Flask, request, render_template, jsonify, redirect, url_for, session
from flask_cors import CORS
import logging
import traceback
import database
from login import login_bp
from register import register_bp
from video_processor import process_video
import config
import groq_transcription
import concept_detector
import learning_loop
import video_importer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Native SQLite Database
database.init_db()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'clipgenie-saas-platform-secret-key-2026')

# ✅ Enable CORS properly
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Register Blueprints
app.register_blueprint(login_bp)
app.register_blueprint(register_bp)

# Configuration
UPLOAD_FOLDER = os.path.abspath('uploads')
SUMMARIZED_FOLDER = os.path.abspath('summarized_uploads')
STATIC_FOLDER = os.path.abspath('static')
ALLOWED_EXTENSIONS = {'webm', 'mp4'}
MAX_CONTENT_LENGTH = 1024 * 1024 * 1024  # 1GB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SUMMARIZED_FOLDER'] = SUMMARIZED_FOLDER
app.config['STATIC_FOLDER'] = STATIC_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SUMMARIZED_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.context_processor
def inject_globals():
    """Globally inject current user and active route to all templates."""
    return {
        'current_user': session.get('user'),
        'current_path': request.path
    }

# ==================== Main Public Pages ====================

@app.route('/')
def home():
    """ClipGenie Landing Homepage"""
    return render_template('home.html')

@app.route('/features')
def features():
    """Features Showcase Page"""
    return render_template('features.html')

@app.route('/pricing')
def pricing():
    """Pricing Plans & FAQ Page"""
    return render_template('pricing.html')

@app.route('/reviews')
def reviews():
    """User Testimonials & Reviews Page"""
    return render_template('reviews.html')

@app.route('/license')
def license_page():
    """Open Source MIT License Page"""
    return render_template('license.html')

# ==================== Video Processing App ====================

@app.route('/app', methods=['GET', 'POST'])
@app.route('/process', methods=['GET', 'POST'])
def app_page():
    """Main Video Processing Studio"""
    if request.method == 'POST':
        try:
            # Check if user submitted a video URL link or uploaded a file
            video_url = request.form.get('video_url', '').strip()
            file = request.files.get('file')

            if not file and not video_url:
                return jsonify({'error': "Please select a video file or paste a video URL link."}), 400

            filename = None
            orig_filename = None

            if video_url:
                logger.info(f"Downloading video from URL in Video Studio: {video_url}")
                dl_info = video_importer.download_video_from_url(video_url)
                filename = os.path.abspath(dl_info['upload_path'])
                orig_filename = dl_info.get('title', 'Imported Video')
            elif file and file.filename != '':
                if not allowed_file(file.filename):
                    return jsonify({'error': 'Invalid file format. Please upload an MP4 or WebM video.'}), 400
                filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                filename = os.path.abspath(filename)
                logger.info(f"Saving uploaded file to: {filename}")
                file.save(filename)
                logger.info(f"File saved successfully: {filename}")
                orig_filename = file.filename
            else:
                return jsonify({'error': "No selected file or video link provided."}), 400

            user_input = request.form.get('prompt', '').strip()
            if not user_input:
                user_input = "key highlights"
            logger.info(f"Processing video with prompt: '{user_input}'")

            # Enforce user authentication before video processing
            user_id = None
            if session.get('user'):
                user_id = str(session['user'].get('id') or session['user'].get('uid'))

            if not user_id:
                logger.warning("Rejecting video processing: user is not logged in")
                return jsonify({
                    'error': 'Sign in required. Please log in or create an account to process videos.',
                    'require_login': True
                }), 401

            # Process video using Whisper + Sentence Transformers + MoviePy
            result = process_video(
                filename, 
                user_input, 
                app.config['UPLOAD_FOLDER'], 
                app.config['SUMMARIZED_FOLDER'],
                user_id
            )

            # Move the output video to the static folder for web playback
            output_video_filename = os.path.basename(result['local_path'])
            static_video_path = os.path.join(app.config['STATIC_FOLDER'], output_video_filename)
            if os.path.exists(static_video_path):
                try:
                    os.remove(static_video_path)
                except Exception as e:
                    logger.warning(f"Could not remove existing video at {static_video_path}: {e}")
            shutil.move(result['local_path'], static_video_path)

            video_id = os.path.splitext(os.path.basename(filename))[0]

            # Register lecture in practice index so it is immediately studyable in Interactive Practice
            video_importer.register_lecture({
                "id": video_id,
                "title": orig_filename or "Processed Video",
                "filename": os.path.basename(filename),
                "video_url": f"/static/{os.path.basename(filename)}" if os.path.exists(os.path.join(app.config['STATIC_FOLDER'], os.path.basename(filename))) else f"/uploads/{os.path.basename(filename)}",
                "duration_str": result.get('duration', '0:00'),
                "source": "studio_upload",
                "concepts_count": 0
            })

            # Save metadata JSON with video_id bridge
            metadata = {
                'output_video_path': f"/static/{output_video_filename}",
                'keyword': user_input,
                'video_duration': result['duration'],
                'short_video_timestamps': result['timestamps'],
                'original_filename': orig_filename,
                'video_id': video_id
            }
            metadata_filename = f"{os.path.splitext(output_video_filename)[0]}_metadata.json"
            metadata_path = os.path.join(app.config['SUMMARIZED_FOLDER'], metadata_filename)
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)

            # Store into user session recent history
            if 'history' not in session:
                session['history'] = []
            session['history'].insert(0, metadata)
            session['history'] = session['history'][:10]
            session.modified = True

            # Redirect to videoplayer.html with metadata path
            return redirect(url_for('videoplayer', metadata_path=metadata_path))

        except ValueError as ve:
            logger.warning(f"Validation error in request processing: {str(ve)}")
            return jsonify({'error': str(ve)}), 400
        except Exception as e:
            logger.error(f"Error in request processing: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({'error': str(e)}), 500

    return render_template('app.html')

# ==================== Video Player ====================

@app.route('/videoplayer')
def videoplayer():
    metadata_path = request.args.get('metadata_path')
    if not metadata_path or not os.path.exists(metadata_path):
        return render_template('videoplayer.html',
                               output_video_path='/static/tedtalk.mp4',
                               keyword='Key Concept Landmarks',
                               video_duration='00:03:45',
                               short_video_timestamps='00:00:26 - 00:01:16, 00:05:20 - 00:06:05',
                               video_id='tedtalk')

    return render_template('videoplayer.html', 
                          output_video_path=metadata['output_video_path'],
                          keyword=metadata['keyword'],
                          video_duration=metadata['video_duration'],
                          short_video_timestamps=metadata['short_video_timestamps'],
                          video_id=metadata.get('video_id', 'tedtalk'))

# ==================== User Profile & Auth Utilities ====================

@app.route('/profile')
@app.route('/dashboard')
def profile():
    """User account dashboard with learning analytics"""
    user = session.get('user')
    if not user:
        return redirect(url_for('login.login_page'))

    user_id = user.get('id') or 1
    stats = database.get_user_stats(user_id)
    session_history = session.get('history', [])

    return render_template('profile.html', user=user, stats=stats, history=session_history)

@app.route('/logout')
def logout():
    """Clear server session and redirect home"""
    user_email = session.get('user', {}).get('email', 'Guest')
    session.clear()
    logger.info(f"User logged out: {user_email}")
    return redirect(url_for('home'))

@app.route('/api/user')
def api_user():
    """API endpoint to check current auth state"""
    user = session.get('user')
    if user:
        return jsonify({'authenticated': True, 'user': user})
    return jsonify({'authenticated': False, 'user': None})

@app.route('/demo-login')
def demo_login():
    """Instant one-click sample learner login"""
    demo_user = database.get_user_by_email('demo.learner@clipgenie.ai')
    if not demo_user:
        database.init_db()
        demo_user = database.get_user_by_email('demo.learner@clipgenie.ai')
    session['user'] = demo_user
    session.permanent = True
    logger.info(f"One-click sample learner logged in: {demo_user['email']}")
    next_url = request.args.get('next', url_for('practice'))
    return redirect(next_url)

# ==================== User Progress Persistence Routes ====================

@app.route('/api/practice/user-progress', methods=['GET'])
def api_get_user_progress():
    """Retrieves saved concept mastery and independence metrics for the current user."""
    user = session.get('user')
    video_id = request.args.get('video_id', 'tedtalk')
    if not user:
        return jsonify({
            'authenticated': False,
            'video_id': video_id,
            'concepts': {},
            'total_practiced': 0,
            'mastered_count': 0,
            'independence_rate': '--'
        })
    user_id = user.get('id') or 1
    progress = database.get_user_lecture_progress(user_id, video_id)
    return jsonify({
        'authenticated': True,
        'user': user,
        'video_id': video_id,
        'concepts': progress['concepts'],
        'total_practiced': progress['total_practiced'],
        'mastered_count': progress['mastered_count'],
        'independence_rate': progress['independence_rate']
    })

@app.route('/api/practice/save-progress', methods=['POST'])
def api_save_user_progress():
    """Persists a concept attempt, retry score, transfer score, and mastery status."""
    user = session.get('user')
    data = request.get_json() or {}
    video_id = data.get('video_id', 'tedtalk')
    concept_id = data.get('concept_id')
    concept_title = data.get('concept_title', '')
    attempt1_score = data.get('attempt1_score')
    attempt2_score = data.get('attempt2_score')
    transfer_score = data.get('transfer_score')
    mastery_status = data.get('mastery_status')
    handled_without_help = data.get('handled_without_help')

    if not concept_id:
        return jsonify({'error': 'concept_id is required'}), 400

    if not user:
        return jsonify({
            'saved': False,
            'authenticated': False,
            'message': 'Progress tracked in guest session. Sign in to sync across devices.'
        }), 200

    user_id = user.get('id') or 1
    saved = database.save_concept_progress(
        user_id=user_id,
        video_id=video_id,
        concept_id=concept_id,
        concept_title=concept_title,
        attempt1_score=attempt1_score,
        attempt2_score=attempt2_score,
        transfer_score=transfer_score,
        mastery_status=mastery_status,
        handled_without_help=handled_without_help
    )

    updated_summary = database.get_user_lecture_progress(user_id, video_id)
    return jsonify({
        'saved': saved,
        'authenticated': True,
        'independence_rate': updated_summary['independence_rate'],
        'mastered_count': updated_summary['mastered_count']
    })

# ==================== Hackathon Practice Loop Routes ====================

def resolve_video_info(video_id=None):
    """Resolves video metadata and local file path for a lecture ID."""
    lectures = video_importer.get_lectures_index()
    target_lecture = None
    if video_id:
        for l in lectures:
            if l.get('id') == video_id:
                target_lecture = l
                break
    if not target_lecture and lectures:
        target_lecture = lectures[0]
        
    if target_lecture:
        vid_filename = target_lecture.get('filename', 'tedtalk.mp4')
        vid_path = os.path.join(config.STATIC_DIR, vid_filename)
        if not os.path.exists(vid_path):
            vid_path = os.path.join(config.UPLOADS_DIR, vid_filename)
        return target_lecture, vid_path
        
    default_meta = {
        'id': 'tedtalk',
        'title': 'The Coming Wave: AI as a Digital Species (Mustafa Suleyman)',
        'video_url': '/static/tedtalk.mp4'
    }
    return default_meta, os.path.join(config.STATIC_DIR, 'tedtalk.mp4')

@app.route('/practice')
def practice():
    """ClipGenie Targeted Retrieval Practice Studio (Features 1 - 7)"""
    return render_template('practice.html')

@app.route('/instructor')
def instructor_view():
    """Instructor Aggregate Gap Intelligence View (Feature 8)"""
    return render_template('instructor_view.html')

@app.route('/api/practice/lectures', methods=['GET'])
def api_practice_lectures():
    """List all available lectures (Demo preset + uploaded/imported videos)"""
    return jsonify({
        'lectures': video_importer.get_lectures_index()
    })

@app.route('/api/practice/import-url', methods=['POST'])
def api_import_url():
    """Download video from YouTube, Facebook, or web links, transcribe, and extract concepts."""
    try:
        data = request.get_json() or {}
        url = data.get('url', '').strip()
        if not url:
            return jsonify({'error': 'Please provide a valid video URL.'}), 400
            
        logger.info(f"Importing video from link: {url}")
        dl_info = video_importer.download_video_from_url(url)
        
        process_res = video_importer.process_and_index_lecture(
            dl_info['upload_path'],
            custom_title=dl_info['title'],
            video_id=dl_info['id'],
            source='url_import'
        )
        
        return jsonify({
            'success': True,
            'lecture': process_res['lecture'],
            'concepts_count': len(process_res.get('concepts', [])),
            'message': f"Successfully imported '{dl_info['title']}'!"
        })
    except ValueError as ve:
        logger.warning(f"Validation error importing URL: {ve}")
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        logger.error(f"Error importing video from URL: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f"Failed to import video from URL: {str(e)}"}), 500

@app.route('/api/practice/upload-video', methods=['POST'])
def api_upload_video():
    """Upload a local video file, transcribe with Groq, and extract curriculum concepts."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded.'}), 400
            
        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({'error': 'Empty filename.'}), 400
            
        safe_name = video_importer.sanitize_filename(file.filename)
        base_name, ext = os.path.splitext(safe_name)
        if ext.lower() not in ('.mp4', '.webm', '.mov', '.mkv'):
            return jsonify({'error': 'Please upload a video file (.mp4, .webm, .mov)'}), 400
            
        save_path = os.path.join(config.UPLOADS_DIR, safe_name)
        file.save(save_path)
        
        process_res = video_importer.process_and_index_lecture(
            save_path,
            custom_title=base_name.replace('_', ' ').title(),
            video_id=base_name,
            source='local_upload'
        )
        
        return jsonify({
            'success': True,
            'lecture': process_res['lecture'],
            'concepts_count': len(process_res.get('concepts', [])),
            'message': f"Successfully uploaded and analyzed '{file.filename}'!"
        })
    except ValueError as ve:
        logger.warning(f"Validation error in uploaded video: {ve}")
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        logger.error(f"Error uploading video: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f"Failed to process uploaded video: {str(e)}"}), 500

@app.route('/api/practice/load', methods=['GET'])
def api_practice_load():
    """Load concepts and lecture metadata for specified or default lecture"""
    video_id = request.args.get('video_id')
    force_auto = request.args.get('force_auto', 'false').lower() in ('true', '1')
    mode = request.args.get('mode', 'auto')
    
    lecture_meta, video_path = resolve_video_info(video_id)
    
    segments = groq_transcription.get_or_create_transcript(video_path, force_live=(mode == 'online'))
    concepts = concept_detector.get_lecture_concepts(video_path, segments, force_auto=force_auto)
    
    return jsonify({
        'video_id': lecture_meta.get('id', 'tedtalk'),
        'video_file': lecture_meta.get('video_url', f"/static/{os.path.basename(video_path)}"),
        'title': lecture_meta.get('title', 'Lecture Video'),
        'concepts': concepts,
        'mode': mode
    })

@app.route('/api/practice/generate-prompt', methods=['POST'])
def api_generate_prompt():
    """Feature 3: Retrieval Prompt Generation (Grounded strictly in segment transcript)"""
    data = request.get_json() or {}
    concept_id = data.get('concept_id', 'concept_1')
    concept_title = data.get('concept_title', 'AI Inflection Point')
    start = float(data.get('start', 0))
    end = float(data.get('end', 60))
    mode = data.get('mode', 'auto')
    video_id = data.get('video_id')
    occurrences = data.get('occurrences')
    
    _, video_path = resolve_video_info(video_id)
    segments = groq_transcription.get_or_create_transcript(video_path)
    transcript_text = concept_detector.get_transcript_for_concept(segments, start, end, occurrences=occurrences)
    
    result = learning_loop.generate_retrieval_prompt(concept_id, concept_title, transcript_text, mode=mode)
    return jsonify(result)

@app.route('/api/practice/feedback', methods=['POST'])
def api_practice_feedback():
    """Feature 4: Gap-Based Feedback (STRICT: NEVER reveals the correct answer)"""
    data = request.get_json() or {}
    concept_id = data.get('concept_id', 'concept_1')
    question = data.get('question', '')
    student_answer = data.get('student_answer', '')
    start = float(data.get('start', 0))
    end = float(data.get('end', 60))
    mode = data.get('mode', 'auto')
    video_id = data.get('video_id')
    occurrences = data.get('occurrences')
    
    _, video_path = resolve_video_info(video_id)
    segments = groq_transcription.get_or_create_transcript(video_path)
    transcript_text = concept_detector.get_transcript_for_concept(segments, start, end, occurrences=occurrences)
    
    feedback = learning_loop.evaluate_gap_feedback(concept_id, question, student_answer, transcript_text, mode=mode)
    return jsonify(feedback)

@app.route('/api/practice/retry', methods=['POST'])
def api_practice_retry():
    """Feature 5: Retry Flow & Comparison Scoring"""
    data = request.get_json() or {}
    concept_id = data.get('concept_id', 'concept_1')
    attempt_1_score = int(data.get('attempt_1_score', 50))
    attempt_1_answer = data.get('attempt_1_answer', '')
    attempt_2_answer = data.get('attempt_2_answer', '')
    start = float(data.get('start', 0))
    end = float(data.get('end', 60))
    mode = data.get('mode', 'auto')
    video_id = data.get('video_id')
    occurrences = data.get('occurrences')
    
    _, video_path = resolve_video_info(video_id)
    segments = groq_transcription.get_or_create_transcript(video_path)
    transcript_text = concept_detector.get_transcript_for_concept(segments, start, end, occurrences=occurrences)
    
    result = learning_loop.evaluate_retry(concept_id, attempt_1_score, attempt_1_answer, attempt_2_answer, transcript_text, mode=mode)
    return jsonify(result)

@app.route('/api/practice/transfer-question', methods=['POST'])
def api_transfer_question():
    """Feature 6: Transfer Check Question (Cold, unscaffolded)"""
    data = request.get_json() or {}
    concept_id = data.get('concept_id', 'concept_1')
    concept_title = data.get('concept_title', 'Concept')
    start = float(data.get('start', 0))
    end = float(data.get('end', 60))
    mode = data.get('mode', 'auto')
    video_id = data.get('video_id')
    occurrences = data.get('occurrences')
    
    _, video_path = resolve_video_info(video_id)
    segments = groq_transcription.get_or_create_transcript(video_path)
    transcript_text = concept_detector.get_transcript_for_concept(segments, start, end, occurrences=occurrences)
    
    result = learning_loop.generate_transfer_question(concept_id, concept_title, transcript_text, mode=mode)
    return jsonify(result)

@app.route('/api/practice/transfer-eval', methods=['POST'])
def api_transfer_eval():
    """Feature 6 & 7: Transfer Answer Evaluation & Mastery Determination"""
    data = request.get_json() or {}
    concept_id = data.get('concept_id', 'concept_1')
    transfer_question = data.get('transfer_question', '')
    student_answer = data.get('student_answer', '')
    start = float(data.get('start', 0))
    end = float(data.get('end', 60))
    mode = data.get('mode', 'auto')
    video_id = data.get('video_id')
    occurrences = data.get('occurrences')
    
    _, video_path = resolve_video_info(video_id)
    segments = groq_transcription.get_or_create_transcript(video_path)
    transcript_text = concept_detector.get_transcript_for_concept(segments, start, end, occurrences=occurrences)
    
    result = learning_loop.evaluate_transfer_answer(concept_id, transfer_question, student_answer, transcript_text, mode=mode)
    return jsonify(result)

if __name__ == '__main__':
    # use_reloader=False prevents watchdog from interrupting AI video processing
    app.run(debug=True, use_reloader=False, port=5000)