from flask import Flask, render_template, jsonify, request
from config import Config
from extensions import db
from models import User # important: import user
from sqlalchemy import func
import os

# Explicitly import the blueprints directly from their route files
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.expert import expert_bp
from routes.farmer import farmer_bp

# Import models to ensure SQLAlchemy detects them during db.create_all()
from models import User, Question, ExpertRating, Announcement, AnnouncementReaction

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

@app.route('/')
def index():
    # Public entry point (login/registration gate)
    return render_template('index.html')

# =====================================================================
# VIEW RENDERING ROUTES FOR FRONTEND
# =====================================================================

@app.route('/public-feed')
def render_public_feed():
    """ Serves the HTML template containing the feed UI and leaderboard column """
    return render_template('feed.html')

@app.route('/expert/dashboard')
def expert_dashboard_page():
    """ Serves the HTML workspace layout dedicated to agricultural experts """
    return render_template('expert_dashboard.html')

# =====================================================================
# PUBLIC ENGAGEMENT & KNOWLEDGE BASE PLUGINS (APIs)
# =====================================================================

@app.route('/api/public-feed', methods=['GET'])
def get_universal_knowledge_feed():
    """
    Fetches all questions that have been answered by experts and verified
    by an admin, accompanied by compiled engagement scores.
    """
    public_questions = Question.query.filter_by(is_verified=True).order_by(Question.id.desc()).all()
    
    feed_data = []
    for q in public_questions:
        farmer = User.query.get(q.farmer_id)
        expert = User.query.get(q.assigned_expert_id) if q.assigned_expert_id else None
        
        # Calculate dynamic average star rating safely from our ratings table
        avg_stars = db.session.query(func.avg(ExpertRating.stars)).filter(ExpertRating.question_id == q.id).scalar() or 0
        
        feed_data.append({
            "id": q.id,
            "category": q.category,
            "question": q.question,
            "farmer_name": farmer.fullname if farmer else "Anonymous Farmer",
            "expert_name": expert.fullname if expert else "Agrosphere Expert",
            "answer": q.answer,
            "likes": getattr(q, 'likes', 0),
            "dislikes": getattr(q, 'dislikes', 0),
            "rating_avg": round(float(avg_stars), 1),
            "answered_at": q.answered_at.strftime("%d %b %Y, %H:%M") if q.answered_at else "Recent"
        })
        
    return jsonify(feed_data), 200


@app.route('/api/react/<int:qid>', methods=['POST'])
def react_to_answer(qid):
    """ Allows users to increment upvotes (likes) or downvotes (dislikes) on a solution. """
    data = request.get_json() or {}
    reaction_type = data.get('type') # Expected: 'like' or 'dislike'
    
    q = Question.query.get(qid)
    if not q:
        return jsonify({"error": "Question not found"}), 404
        
    if reaction_type == 'like':
        q.likes = (q.likes or 0) + 1
    elif reaction_type == 'dislike':
        q.dislikes = (q.dislikes or 0) + 1
    else:
        return jsonify({"error": "Invalid reaction context token"}), 400
        
    db.session.commit()
    return jsonify({"likes": q.likes, "dislikes": q.dislikes}), 200

@app.route('/api/rate/<int:qid>', methods=['POST'])
def rate_answer(qid):
    """ Allows users to drop a 1 to 5 star rating down on an answer. """
    data = request.get_json() or {}
    stars = int(data.get('stars', 0))
    rater_id = data.get('user_id') # Pass the active user session ID from frontend

    if stars < 1 or stars > 5:
        return jsonify({"error": "Ratings must exist between 1 to 5 stars"}), 400
        
    q = Question.query.get(qid)
    if not q:
        return jsonify({"error": "Question record target missing"}), 404

    # Update prior rating entry if it exists, otherwise instantiate a new one
    existing_rating = ExpertRating.query.filter_by(question_id=qid, rater_id=rater_id).first()
    if existing_rating:
        existing_rating.stars = stars
    else:
        new_rating = ExpertRating(question_id=qid, rater_id=rater_id, stars=stars)
        db.session.add(new_rating)
        
    db.session.commit()
    return jsonify({"message": "Rating recorded successfully!"}), 200


@app.route('/api/expert-leaderboard', methods=['GET'])
def get_expert_leaderboard():
    """ Ranks active system experts according to verified answers volume and satisfaction scores. """
    experts = User.query.filter_by(role='expert').all()
    leaderboard = []
    
    for exp in experts:
        # Filter all verified questions handled by this expert
        verified_qs = Question.query.filter_by(assigned_expert_id=exp.id, is_verified=True).all()
        total_answers = len(verified_qs)
        
        if total_answers > 0:
            q_ids = [q.id for q in verified_qs]
            avg_rating = db.session.query(func.avg(ExpertRating.stars)).filter(ExpertRating.question_id.in_(q_ids)).scalar() or 0
        else:
            avg_rating = 0.0
            
        leaderboard.append({
            "fullname": exp.fullname,
            "total_answers": total_answers,
            "rating_score": round(float(avg_rating), 1)
        })
        
    # Sort: Most answers first. Ties broken by highest average rating.
    leaderboard.sort(key=lambda x: (x['total_answers'], x['rating_score']), reverse=True)
    return jsonify(leaderboard), 200


# Register blueprints with explicit variables
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(expert_bp, url_prefix='/expert')
app.register_blueprint(farmer_bp, url_prefix='/farmer')

@app.route('/register')
def register_page():
    return render_template('register.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("Database created!")
        port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
   