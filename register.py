"""
register.py - Native Authentication Registration Blueprint
Creates new user accounts in local SQLite database with password hashing.
"""

from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for
import logging
import database

logger = logging.getLogger(__name__)

register_bp = Blueprint('register', __name__)

@register_bp.route('/register', methods=['GET'])
@register_bp.route('/signup', methods=['GET'])
def register_page():
    if session.get('user'):
        return redirect(url_for('practice'))
    return render_template('register.html')

@register_bp.route('/register', methods=['POST'])
def register():
    try:
        # Support both JSON payload and standard form data
        if request.is_json:
            data = request.get_json() or {}
            email = data.get('email', '').strip()
            password = data.get('password', '')
            first_name = data.get('firstName', '').strip()
            last_name = data.get('lastName', '').strip()
        else:
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            first_name = request.form.get('firstName', '').strip()
            last_name = request.form.get('lastName', '').strip()

        if not email or not password or not first_name:
            return jsonify({'error': 'First name, email, and password are required.'}), 400

        user, error = database.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        if error or not user:
            return jsonify({'error': error or 'Registration could not be completed.'}), 400

        # Establish server-side Flask session
        session['user'] = user
        session.permanent = True

        logger.info(f"Native registration successful: {user['email']} (ID: {user['id']})")
        return jsonify({
            'success': True,
            'message': 'Account created successfully',
            'user': user,
            'redirect': url_for('practice')
        }), 201

    except Exception as e:
        logger.error(f"Unexpected error in register endpoint: {e}")
        return jsonify({'error': f"Registration error: {str(e)}"}), 500
