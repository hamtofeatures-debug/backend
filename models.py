from extensions import db
from datetime import datetime
from flask_login import UserMixin
from datetime import datetime


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    language = db.Column(db.String(20), default='English')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_suspended = db.Column(db.Boolean, default=False)
    specialization = db.Column(db.String(50), nullable=True)
    blue_tick = db.Column(db.Boolean, default=False)
    verification_expires_at = db.Column(db.DateTime)

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
    # Link the business profile to its login account
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    business_name = db.Column(db.String(200), nullable=False)
    services = db.Column(db.Text, nullable=False)
    phone = db.Column(db.String(20), nullable=True)

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
    is_published = db.Column(db.Boolean, default=False)

    # Relationship to attached photos (farmer can upload photos with question)
    photos = db.relationship('QuestionPhoto', backref='question', lazy=True,
                              cascade='all, delete-orphan')


class QuestionPhoto(db.Model):
    """Photos a farmer attaches to a question."""
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    url = db.Column(db.String(300), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ExpertRating(db.Model):
    """Rating given to an expert after answering a question"""
    id = db.Column(db.Integer, primary_key=True)
    expert_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
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
    """Articles published by experts, with optional photos."""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    expert_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    photos = db.relationship('ArticlePhoto', backref='article', lazy=True,
                              cascade='all, delete-orphan')


class ArticlePhoto(db.Model):
    """Photos uploaded with an expert article."""
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'), nullable=False)
    url = db.Column(db.String(300), nullable=False)


class Post(db.Model):
    """Free-form community posts created by farmers, with optional photos."""
    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    photos = db.relationship('PostPhoto', backref='post', lazy=True,
                              cascade='all, delete-orphan')


class PostPhoto(db.Model):
    """Photos attached to a farmer's community post."""
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    url = db.Column(db.String(300), nullable=False)


class BusinessPost(db.Model):
    """Posts created by business accounts - visible to farmers, experts and admin."""
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    likes_count = db.Column(db.Integer, default=0)
    views_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    media = db.relationship('BusinessPostMedia', backref='post', lazy=True,
                             cascade='all, delete-orphan')


class BusinessPostMedia(db.Model):
    """Photos or videos attached to a business post."""
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('business_post.id'), nullable=False)
    url = db.Column(db.String(300), nullable=False)
    type = db.Column(db.String(10), default='image')  # 'image' or 'video'

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    id          = db.Column(db.Integer, primary_key=True)
    sender_id   = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content     = db.Column(db.Text, nullable=False)
    is_read     = db.Column(db.Boolean, default=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    sender   = db.relationship('User', foreign_keys=[sender_id])
    receiver = db.relationship('User', foreign_keys=[receiver_id])

class SupportMessage(db.Model):
    __tablename__ = 'support_messages'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message    = db.Column(db.Text, nullable=False)
    status     = db.Column(db.String(20), default='Unread')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='support_messages')



class Payment(db.Model):
     id = db.Column(db.Integer, primary_key=True)

user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

amount = db.Column(db.Float, nullable=False)
product_type = db.Column(db.String(30), nullable=False)

provider = db.Column(db.String(20), nullable=False)
    # mtn / airtel

reference = db.Column(db.String(100), unique=True, nullable=False)

external_transaction_id = db.Column(db.String(100), nullable=True)

status = db.Column(db.String(20), default='pending')
    # pending / processing / paid / failed

created_at = db.Column(db.DateTime, default=datetime.utcnow)

expires_at = db.Column(db.DateTime)