from flask import Blueprint, request, jsonify, render_template
from extensions import db
from models import Question, User

business_bp = Blueprint('business', __name__)

@business_bp.route('/')
def home():
   return render_template('business_dashboard.html')