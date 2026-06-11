from extensions import db
from datetime import datetime

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    language = db.Column(db.String(20), default='English')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Farmer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    farm_name = db.Column(db.String(100))
    district = db.Column(db.String(100))
    farm_size = db.Column(db.Float)

class Expert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    specialization = db.Column(db.String(100))
    qualification = db.Column(db.String(100))
    experience = db.Column(db.Integer, default=0)

class Business(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    business_name = db.Column(db.String(200), nullable=False)
    services = db.Column(db.Text, nullable=False)

    location = db.Column(db.String(200))
    description = db.Column(db.Text)

    status = db.Column(db.String(20), default='pending')
    # pending, approved, rejected, suspended

    verification_status = db.Column(db.String(20), default='none')
    # none, verified, premium_verified

    blue_tick = db.Column(db.Boolean, default=False)

    payment_status = db.Column(db.String(20), default='unpaid')
    # unpaid, pending, paid

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Question(db.Model):
    # All these must be indented by 4 spaces
    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    question = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='General')
    status = db.Column(db.String(20), default='pending')
    assigned_expert_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    answer = db.Column(db.Text, nullable=True)
    answer_verified = db.Column(db.Boolean, default=False)
    admin_note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    answered_at = db.Column(db.DateTime, nullable=True)
    # The new field must also be indented at the same level
    is_published = db.Column(db.Boolean, default=False)

class ExpertRating(db.Model):
    """Rating given to an expert after answering a question"""
    id = db.Column(db.Integer, primary_key=True)
    expert_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rater_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=True)
    stars = db.Column(db.Integer, nullable=False)  # 1-5
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Announcement(db.Model):
    """Admin posts visible to all users"""
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='General')
    likes = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AnnouncementReaction(db.Model):
    """Track who liked/disliked an announcement"""
    id = db.Column(db.Integer, primary_key=True)
    announcement_id = db.Column(db.Integer, db.ForeignKey('announcement.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reaction = db.Column(db.String(10), nullable=False)  # 'like' or 'dislike'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Articles(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    expert_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # Add this field:
    is_approved = db.Column(db.Boolean, default=False)