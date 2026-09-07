"""
database.py - Native SQLite Database for ClipGenie
Provides local, zero-external-dependency authentication, user profiles,
and persistent student concept mastery tracking.
"""

import os
import sqlite3
import logging
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash

logger = logging.getLogger(__name__)

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "clipgenie.db"))

def get_db_connection():
    """Returns a connection to the SQLite database with Row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """Initializes database schema and ensures demo accounts are seeded."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Users Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 2. User Concept Progress Table (tracks attempts, retries, transfer, and mastery per concept)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            video_id TEXT NOT NULL,
            concept_id TEXT NOT NULL,
            concept_title TEXT DEFAULT '',
            attempt1_score INTEGER DEFAULT 0,
            attempt2_score INTEGER DEFAULT 0,
            transfer_score INTEGER DEFAULT 0,
            mastery_status TEXT DEFAULT 'Not Started',
            handled_without_help INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, video_id, concept_id)
        );
    """)

    conn.commit()
    conn.close()
    logger.info(f"ClipGenie SQLite database initialized at: {DB_PATH}")

    # Seed demo account for instant 1-click judging evaluation
    seed_demo_user()

def seed_demo_user():
    """Provisions a pre-configured demo student with realistic mastery history."""
    demo_email = "demo.learner@clipgenie.ai"
    user = get_user_by_email(demo_email)
    if not user:
        created, _ = create_user(
            email=demo_email,
            password="DemoPassword2026!",
            first_name="Alex",
            last_name="Learner"
        )
        if created:
            user_id = created["id"]
            # Pre-seed concept mastery for tedtalk demo lecture
            save_concept_progress(
                user_id=user_id,
                video_id="tedtalk",
                concept_id="concept_1",
                concept_title="The AI Inflection Point & Digital Companions",
                attempt1_score=90,
                attempt2_score=0,
                transfer_score=85,
                mastery_status="Mastered",
                handled_without_help=1
            )
            save_concept_progress(
                user_id=user_id,
                video_id="tedtalk",
                concept_id="concept_2",
                concept_title="The Containment Problem & Technological Proliferation",
                attempt1_score=55,
                attempt2_score=85,
                transfer_score=80,
                mastery_status="Mastered",
                handled_without_help=0
            )
            logger.info("Seeded demo student account and initial mastery records.")

def create_user(email, password, first_name, last_name=""):
    """
    Creates a new user with hashed password.
    Returns (user_dict, error_message).
    """
    email = (email or "").strip().lower()
    first_name = (first_name or "").strip()
    last_name = (last_name or "").strip()

    if not email or "@" not in email or "." not in email:
        return None, "Please provide a valid email address."

    if not password or len(password) < 6:
        return None, "Password must be at least 6 characters long."

    if not first_name:
        return None, "First name is required."

    password_hash = generate_password_hash(password)

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO users (email, password_hash, first_name, last_name)
            VALUES (?, ?, ?, ?);
        """, (email, password_hash, first_name, last_name))
        conn.commit()
        user_id = cursor.lastrowid
        display_name = f"{first_name} {last_name}".strip()
        user = {
            "id": user_id,
            "uid": str(user_id),
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "displayName": display_name
        }
        return user, None
    except sqlite3.IntegrityError:
        return None, "An account with this email address already exists. Please sign in."
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return None, f"Registration failed: {str(e)}"
    finally:
        conn.close()

def verify_user(email, password):
    """
    Verifies user credentials.
    Returns (user_dict, error_message).
    """
    email = (email or "").strip().lower()
    if not email or not password:
        return None, "Email and password are required."

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM users WHERE email = ?;", (email,))
        row = cursor.fetchone()
        if not row:
            return None, "Invalid email or password. Please check your credentials."

        if not check_password_hash(row["password_hash"], password):
            return None, "Invalid email or password. Please check your credentials."

        display_name = f"{row['first_name']} {row['last_name']}".strip() or row["email"].split("@")[0]
        user = {
            "id": row["id"],
            "uid": str(row["id"]),
            "email": row["email"],
            "first_name": row["first_name"],
            "last_name": row["last_name"],
            "displayName": display_name
        }
        return user, None
    except Exception as e:
        logger.error(f"Error verifying user: {e}")
        return None, f"Authentication error: {str(e)}"
    finally:
        conn.close()

def get_user_by_email(email):
    """Fetches user record by email."""
    email = (email or "").strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, first_name, last_name FROM users WHERE email = ?;", (email,))
    row = cursor.fetchone()
    conn.close()
    if row:
        display_name = f"{row['first_name']} {row['last_name']}".strip()
        return {
            "id": row["id"],
            "uid": str(row["id"]),
            "email": row["email"],
            "first_name": row["first_name"],
            "last_name": row["last_name"],
            "displayName": display_name
        }
    return None

def get_user_by_id(user_id):
    """Fetches user record by numeric ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, first_name, last_name FROM users WHERE id = ?;", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        display_name = f"{row['first_name']} {row['last_name']}".strip()
        return {
            "id": row["id"],
            "uid": str(row["id"]),
            "email": row["email"],
            "first_name": row["first_name"],
            "last_name": row["last_name"],
            "displayName": display_name
        }
    return None

def save_concept_progress(user_id, video_id, concept_id, concept_title="",
                          attempt1_score=None, attempt2_score=None,
                          transfer_score=None, mastery_status=None, handled_without_help=None):
    """
    Saves or updates concept progress for a student.
    Upserts into user_progress table.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check existing record
        cursor.execute("""
            SELECT * FROM user_progress
            WHERE user_id = ? AND video_id = ? AND concept_id = ?;
        """, (user_id, video_id, concept_id))
        existing = cursor.fetchone()

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        if existing:
            # Preserve existing values if not provided
            a1 = attempt1_score if attempt1_score is not None else existing["attempt1_score"]
            a2 = attempt2_score if attempt2_score is not None else existing["attempt2_score"]
            ts = transfer_score if transfer_score is not None else existing["transfer_score"]
            m_stat = mastery_status if mastery_status is not None else existing["mastery_status"]
            
            if handled_without_help is not None:
                hwh = 1 if handled_without_help else 0
            else:
                hwh = existing["handled_without_help"]

            title = concept_title or existing["concept_title"]

            cursor.execute("""
                UPDATE user_progress
                SET concept_title = ?, attempt1_score = ?, attempt2_score = ?,
                    transfer_score = ?, mastery_status = ?, handled_without_help = ?,
                    updated_at = ?
                WHERE id = ?;
            """, (title, a1, a2, ts, m_stat, hwh, now, existing["id"]))
        else:
            a1 = attempt1_score or 0
            a2 = attempt2_score or 0
            ts = transfer_score or 0
            m_stat = mastery_status or "In Progress"
            hwh = 1 if handled_without_help else 0

            cursor.execute("""
                INSERT INTO user_progress (
                    user_id, video_id, concept_id, concept_title,
                    attempt1_score, attempt2_score, transfer_score,
                    mastery_status, handled_without_help, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (user_id, video_id, concept_id, concept_title, a1, a2, ts, m_stat, hwh, now))

        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error saving concept progress: {e}")
        return False
    finally:
        conn.close()

def get_user_lecture_progress(user_id, video_id):
    """
    Returns a dictionary of concept progress records for a user on a specific video,
    plus overall aggregated stats (mastered count, independence rate).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT * FROM user_progress
            WHERE user_id = ? AND video_id = ?;
        """, (user_id, video_id))
        rows = cursor.fetchall()

        concepts_map = {}
        total_attempts = 0
        handled_first_attempt = 0
        mastered_count = 0

        for r in rows:
            c_id = r["concept_id"]
            concepts_map[c_id] = {
                "concept_id": c_id,
                "concept_title": r["concept_title"],
                "attempt1_score": r["attempt1_score"],
                "attempt2_score": r["attempt2_score"],
                "transfer_score": r["transfer_score"],
                "mastery_status": r["mastery_status"],
                "handled_without_help": bool(r["handled_without_help"]),
                "updated_at": r["updated_at"]
            }
            if r["attempt1_score"] > 0:
                total_attempts += 1
                if r["handled_without_help"]:
                    handled_first_attempt += 1
            if r["mastery_status"] == "Mastered":
                mastered_count += 1

        rate = round((handled_first_attempt / total_attempts) * 100) if total_attempts > 0 else None

        return {
            "concepts": concepts_map,
            "total_practiced": total_attempts,
            "mastered_count": mastered_count,
            "independence_rate": f"{rate}%" if rate is not None else "--"
        }
    except Exception as e:
        logger.error(f"Error fetching lecture progress: {e}")
        return {"concepts": {}, "total_practiced": 0, "mastered_count": 0, "independence_rate": "--"}
    finally:
        conn.close()

def get_user_stats(user_id):
    """
    Aggregates lifetime mastery statistics for the user profile page.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT 
                COUNT(*) as total_records,
                SUM(CASE WHEN mastery_status = 'Mastered' THEN 1 ELSE 0 END) as total_mastered,
                SUM(CASE WHEN handled_without_help = 1 THEN 1 ELSE 0 END) as total_independent,
                COUNT(DISTINCT video_id) as total_lectures
            FROM user_progress
            WHERE user_id = ?;
        """, (user_id,))
        stats = cursor.fetchone()

        cursor.execute("""
            SELECT video_id, concept_title, mastery_status, transfer_score, updated_at
            FROM user_progress
            WHERE user_id = ?
            ORDER BY updated_at DESC
            LIMIT 10;
        """, (user_id,))
        recent = [dict(r) for r in cursor.fetchall()]

        total_rec = stats["total_records"] or 0
        total_mast = stats["total_mastered"] or 0
        total_ind = stats["total_independent"] or 0
        rate = round((total_ind / total_rec) * 100) if total_rec > 0 else 0

        return {
            "total_concepts_practiced": total_rec,
            "total_mastered": total_mast,
            "independence_rate": f"{rate}%" if total_rec > 0 else "--",
            "total_lectures": stats["total_lectures"] or 0,
            "recent_activity": recent
        }
    except Exception as e:
        logger.error(f"Error fetching user stats: {e}")
        return {
            "total_concepts_practiced": 0,
            "total_mastered": 0,
            "independence_rate": "--",
            "total_lectures": 0,
            "recent_activity": []
        }
    finally:
        conn.close()
