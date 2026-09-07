"""
login.py - Native Authentication Login Blueprint
Validates email and password against local SQLite database.
"""

from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for
import logging
import database

logger = logging.getLogger(__name__)

login_bp = Blueprint('login', __name__)

@login_bp.route('/login', methods=['GET'])
@login_bp.route('/signin', methods=['GET'])
def login_page():
    if session.get('user'):
        return redirect(url_for('practice'))
    return render_template('login.html')

@login_bp.route('/login', methods=['POST'])
def login():
    try:
        # Support both JSON payload and standard form data
        if request.is_json:
            data = request.get_json() or {}
            email = data.get('email', '').strip()
            password = data.get('password', '')
        else:
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')

        if not email or not password:
            return jsonify({'error': 'Please provide both email and password.'}), 400

        user, error = database.verify_user(email, password)
        if error or not user:
            return jsonify({'error': error or 'Invalid email or password.'}), 401

        # Establish server-side Flask session
        session['user'] = user
        session.permanent = True

        logger.info(f"Native login successful: {user['email']} (ID: {user['id']})")
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'user': user,
            'redirect': url_for('practice')
        }), 200

    except Exception as e:
        logger.error(f"Unexpected error in login endpoint: {e}")
        return jsonify({'error': f"Login error: {str(e)}"}), 500
