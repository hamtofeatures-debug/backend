from flask import Blueprint, request, jsonify, session
from extensions import db
from models import User, Farmer, Expert, Business
from werkzeug.security import generate_password_hash, check_password_hash

auth_bp = Blueprint('auth', __name__)


# ==========================================
# LOGIN ROUTE (now sets session so dashboards work)
# ==========================================
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON request body"}), 400

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user = User.query.filter_by(email=email).first()

    if user and check_password_hash(user.password, password):

        # IMPORTANT: store session so /admin/dashboard, /farmer/dashboard,
        # /expert/dashboard, /business/dashboard can identify the user
        session['user_id'] = user.id
        session['role'] = user.role
        session['fullname'] = user.fullname

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


@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"}), 200

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    fullname = data.get('fullname')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role')

    if not fullname or not email or not password or not role:
        return jsonify({"error": "All fields are required"}), 400

    existing = User.query.filter_by(email=email).first()
    if existing:
        return jsonify({"error": "Email already exists"}), 400

    user = User(
        fullname=fullname,
        email=email,
        password=generate_password_hash(password),
        role=role
    )

    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "Account created successfully"}), 201

    email = data.get('email')
    business_name = data.get('business_name')
    services = data.get('services')
    location = data.get('location')
    description = data.get('description')

    if not email or not business_name or not services:
        return jsonify({"error": "Email, business name and services are required"}), 400

    # The user account (role='business') must already exist from /auth/register
    user = User.query.filter_by(email=email, role='business').first()
    if not user:
        return jsonify({"error": "No business account found for this email. Please register first."}), 404

    existing = Business.query.filter_by(user_id=user.id).first()
    if existing:
        return jsonify({"error": "Business profile already exists for this account"}), 400

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