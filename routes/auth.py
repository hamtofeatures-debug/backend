from flask import Blueprint, request, jsonify, url_for
from extensions import db
from models import User, Farmer, Expert, Business
from werkzeug.security import generate_password_hash, check_password_hash

# Define the blueprint
auth_bp = Blueprint('auth', __name__)

# ==========================================
# 1. REGISTRATION ROUTE
# ==========================================
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON request body"}), 400

    fullname = data.get('fullname')
    email = data.get('email')
    phone = data.get('phone')
    password = data.get('password')
    role = data.get('role')  # admin, expert, farmer
    language = data.get('language', 'English')

    # Basic data validation
    if not fullname or not email or not password or not role:
        return jsonify({"error": "Missing required fields"}), 400
    
    # Check if email already exists
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 400
        
    # Limit Admin accounts to 3
    if role == "admin":
        admin_count = User.query.filter_by(role="admin").count()
        if admin_count >= 3:
            return jsonify({"error": "Maximum number of admins reached"}), 400
        
    # Hash password safely using Werkzeug's supported format
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

    # Create the user object (passing the HASHED password, not raw text)
    user = User(
        fullname=fullname, 
        email=email, 
        phone=phone, 
        password=hashed_password, 
        role=role, 
        language=language
    )

    db.session.add(user)
    db.session.commit()  # Commit here so user.id becomes available

    # Create role-specific records
    if role == "farmer":
        farmer = Farmer(user_id=user.id, farm_name="", district="", farm_size=0)
        db.session.add(farmer)
    elif role == "expert":
        expert = Expert(user_id=user.id, specialization="", qualification="", experience=0)
        db.session.add(expert)

    db.session.commit()

    return jsonify({"message": f"{role.capitalize()} registered successfully!"}), 201


# ==========================================
# 2. LOGIN ROUTE (With Secure Redirect Targets)
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
    
    # Query the user by email
    user = User.query.filter_by(email=email).first()

    # Verify the password using check_password_hash
    if user and check_password_hash(user.password, password):
        
        # Decide where to route the user next based on role validation
        if user.role == 'admin':
            redirect_url = url_for('admin.home')  # Points to /admin/dashboard
        elif user.role == 'expert':
            redirect_url = '/expert/dashboard'  # Or your specific expert view path
        else:
            redirect_url = '/'  # Farmers return to home base
            
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
# BUSINESS REGISTRATION
# ==========================================

@auth_bp.route('/register-business', methods=['POST'])
def register_business():

    data = request.get_json()

    if not data:
        return jsonify({"error": "Missing JSON request body"}), 400

    business_name = data.get('business_name')
    services = data.get('services')
    phone = data.get('phone')
    location = data.get('location')
    description = data.get('description')

    if not business_name or not services:
        return jsonify({
            "error": "Business name and services are required"
        }), 400

    existing = Business.query.filter_by(
        business_name=business_name
    ).first()

    if existing:
        return jsonify({
            "error": "Business already registered"
        }), 400

    business = Business(
        business_name=business_name,
        services=services,
        phone=phone,
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