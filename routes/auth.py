from flask import Blueprint, request, jsonify, session, render_template, url_for, flash, redirect
from flask_login import login_user
from extensions import db, limiter
from models import User, Farmer, Expert, Business
from werkzeug.security import generate_password_hash, check_password_hash

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Safely capture variables whether frontend sends JSON or Form Data
        if request.is_json:
            data = request.get_json() or {}
            fullname = data.get('fullname')
            email = data.get('email')
            password = data.get('password')
            role = data.get('role', 'farmer')
            specialization = data.get('specialization')
        else:
            fullname = request.form.get('fullname')
            email = request.form.get('email')
            password = request.form.get('password')
            role = request.form.get('role', 'farmer')
            specialization = request.form.get('specialization')

        # Prevent crashes if password or email is completely missing
        if not email or not password:
            if request.is_json:
                return jsonify({"error": "Email and password are required"}), 400
            flash("Email and password are required")
            return render_template('register.html')

        role = role.lower()

        # Admin safeguarding downgrade restriction
        if role == 'admin' and email != 'admin@agrosphere.com':
            role = 'farmer'

        # Safely hash the confirmed password string
        password_hash = generate_password_hash(password)

        new_user = User(
            fullname=fullname,
            email=email,
            password=password_hash,
            role=role,
            specialization=specialization if role == 'expert' else None
        )

        db.session.add(new_user)
        db.session.commit()

        if request.is_json:
            return jsonify({"message": "Registration successful", "redirect_to": "/login"}), 201

        return redirect(url_for('login_page'))

    return render_template('register.html')

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    if request.is_json:
        data = request.get_json() or {}
        email = data.get('email')
        password = data.get('password')
    else:
        email = request.form.get('email')
        password = request.form.get('password')

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user = User.query.filter_by(email=email).first()

    if user and check_password_hash(user.password, password):

        if user.is_suspended:
            return jsonify({"error": "This account has been suspended. Contact support."}), 403

        session['user_id'] = user.id
        session['role'] = user.role

        if user.role == 'admin':
            redirect_url = '/admin/dashboard'
        elif user.role == 'expert':
            redirect_url = '/expert/dashboard'
        elif user.role == 'farmer':
            redirect_url = '/farmer/dashboard'
        elif user.role == 'business':
            redirect_url = '/business/dashboard'
        else:
            redirect_url = '/'

        return jsonify({
            "message": f"Welcome back {user.fullname}!",
            "redirect_to": redirect_url,
            "user": {
                "id": user.id,
                "fullname": user.fullname,
                "email": user.email,
                "role": user.role
            }
        }), 200
    else:
        return jsonify({"error": "Invalid email or password"}), 401

# ==========================================
# BUSINESS REGISTRATION (separate step)
# ==========================================
@auth_bp.route('/register-business', methods=['POST'])
def register_business():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    email = data.get('email')
    business_name = data.get('business_name')
    services = data.get('services')
    location = data.get('location')
    description = data.get('description')

    if not email or not business_name or not services:
        return jsonify({"error": "Email, business name and services are required"}), 400

    # Find the user (must already be created with role='business')
    user = User.query.filter_by(email=email, role='business').first()
    if not user:
        return jsonify({"error": "No business account found for this email. Please register first."}), 404

    # Prevent duplicate business profiles
    existing = Business.query.filter_by(user_id=user.id).first()
    if existing:
        return jsonify({"error": "Business profile already exists for this account"}), 409

    business = Business(
        user_id=user.id,
        business_name=business_name,
        services=services,
        location=location,
        description=description,
        status="pending",
        verification_status="none",
        blue_tick=False,
        payment_status="unpaid"
    )

    db.session.add(business)
    db.session.commit()

    return jsonify({
        "message": "Business submitted successfully",
        "status": "pending_admin_approval"
    }), 201

@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    
    # Check if request came from a frontend API or a standard HTML form submission
    if request.is_json:
        return jsonify({"message": "Logged out successfully"}), 200
        
    return redirect(url_for('login_page'))

