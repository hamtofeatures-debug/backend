from flask import Blueprint, request, jsonify
from extensions import db
from models import Question, User

business_bp = Blueprint('business', __name__)

@business_bp.route('/')
def home():
   return jsonify({"message": "Welcome to Business Dashboard!"})