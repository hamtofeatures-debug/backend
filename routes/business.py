import os
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from extensions import db
from models import User, Business, BusinessPost, BusinessPostMedia, Announcement, Question

business_bp = Blueprint('business', __name__)

UPLOAD_FOLDER = os.path.join('static', 'uploads', 'business')
ALLOWED_IMAGE_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_VIDEO_EXT = {'mp4', 'mov', 'webm', 'avi'}


def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set


@business_bp.route('/')
def home():
    return jsonify({"message": "Welcome to Business Dashboard!"})


# ---------------------------------------------------------
# BUSINESS DASHBOARD (GET)
# ---------------------------------------------------------
@business_bp.route('/business/dashboard')
@login_required
def dashboard():
    business = Business.query.filter_by(user_id=current_user.id).first()

    my_posts = BusinessPost.query.filter_by(business_id=current_user.id)\
        .order_by(BusinessPost.created_at.desc()).all()

    stats = {
        "total_posts": len(my_posts),
        "total_likes": sum(p.likes_count for p in my_posts),
        "total_views": sum(p.views_count for p in my_posts),
    }

    announcements = Announcement.query.order_by(Announcement.created_at.desc()).limit(20).all()

    public_qa = Question.query.filter_by(is_published=True)\
        .order_by(Question.answered_at.desc()).limit(20).all()

    # Attach helper attributes the template expects
    for q in public_qa:
        farmer = User.query.get(q.farmer_id)
        q.farmer_name = farmer.fullname if farmer else "Unknown"
        if q.assigned_expert_id:
            expert = User.query.get(q.assigned_expert_id)
            q.assigned_expert = expert.fullname if expert else "Unknown"
        else:
            q.assigned_expert = "Unknown"

    return render_template(
        'business_dashboard.html',
        business=business,
        my_posts=my_posts,
        stats=stats,
        announcements=announcements,
        public_qa=public_qa
    )


# ---------------------------------------------------------
# CREATE POST (POST, with file uploads)
# ---------------------------------------------------------
@business_bp.route('/create-post', methods=['POST'])
def create_post():
    if session.get('role') != 'business':
        return redirect(url_for('index'))

    user_id = session['user_id']
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()

    if not title or not description:
        return redirect(url_for('business_dashboard_page'))

    new_post = BusinessPost(title=title, description=description, business_id=user_id)
    db.session.add(new_post)
    db.session.flush()

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    for photo in request.files.getlist('photos'):
        if photo and photo.filename and allowed_file(photo.filename, ALLOWED_IMAGE_EXT):
            filename = secure_filename(f"post{new_post.id}_{photo.filename}")
            photo.save(os.path.join(UPLOAD_FOLDER, filename))
            db.session.add(BusinessPostMedia(post_id=new_post.id, url=f"/static/uploads/business/{filename}", type='image'))

    for video in request.files.getlist('videos'):
        if video and video.filename and allowed_file(video.filename, ALLOWED_VIDEO_EXT):
            filename = secure_filename(f"post{new_post.id}_{video.filename}")
            video.save(os.path.join(UPLOAD_FOLDER, filename))
            db.session.add(BusinessPostMedia(post_id=new_post.id, url=f"/static/uploads/business/{filename}", type='video'))

    db.session.commit()
    return redirect(url_for('business_dashboard_page'))