import os
from flask import Flask, render_template, redirect, url_for, session, flash, request, Blueprint, current_app
from models.enrollment_model import enroll_student, get_enrollments_by_course
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId
from functools import wraps
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from pymongo import MongoClient
import json
from datetime import datetime
from utils.decorators import role_required, login_required
from models.user_model import get_user_by_id
from routes.course_route import course_routes
from flask_login import LoginManager

login_manager = LoginManager()
login_manager.login_view = 'auth.login'


 
import config

# ───── Setup Flask App ─────
app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY
CORS(app)

# Email config
app.config['MAIL_SERVER'] = config.MAIL_SERVER
app.config['MAIL_PORT'] = config.MAIL_PORT
app.config['MAIL_USE_TLS'] = config.MAIL_USE_TLS
app.config['MAIL_USERNAME'] = config.MAIL_USERNAME
app.config['MAIL_PASSWORD'] = config.MAIL_PASSWORD
app.config['MAIL_DEFAULT_SENDER'] = config.MAIL_DEFAULT_SENDER
mail = Mail(app)

# Token serializer
s = URLSafeTimedSerializer(app.config['SECRET_KEY'])

UPLOAD_FOLDER_PATH = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER_PATH
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ───── MongoDB Connection ─────
client = MongoClient(config.MONGODB_URI)
app.db = client["elearn_demo"]

# Collections
users_collection = app.db["users"]
courses_collection = app.db["courses"]
enrollments_collection = app.db["enrollments"]

# ───── Extensions ─────
bcrypt = Bcrypt(app)
app.bcrypt = bcrypt

# ───── Register Blueprints ─────
from routes.auth_route import auth_bp
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(course_routes)

# ───── Dummy course data ─────
courses_data = {
    "python": {
        "title": "Python for Beginners",
        "description": "Master the basics of Python programming.",
        "instructor": "Jane Doe",
        "image": "python-course.jpg"
    },
    "webdev": {
        "title": "Web Development Bootcamp",
        "description": "Learn HTML, CSS, Flask and build real-world websites.",
        "instructor": "John Smith",
        "image": "webdev-course.jpg"
    },
    "datasci": {
        "title": "Data Science Essentials",
        "description": "Analyze data using Pandas, Numpy, and Matplotlib.",
        "instructor": "Alice Johnson",
        "image": "data-course.jpg"
    }
}


from flask_login import current_user

@app.context_processor
def inject_user():
    return dict(current_user=current_user)



# ───── Forgot Password ─────
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email")
        user = app.db.users.find_one({"email": email})
        if user:
            token = s.dumps(str(user["_id"]), salt="reset-password")
            link = url_for("reset_password", token=token, _external=True)

            msg = Message("E-LEARN Password Reset Request", recipients=[email])
            msg.body = f"Click the link below to reset your password: {link}. Ignore this email if you did not request a password reset."
            mail.send(msg)

            flash("Password reset link sent. Check your email.", "info")
        else:
            flash("Email not found.", "danger")
    return render_template("forgot_password.html")

@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    try:
        user_id = s.loads(token, salt="reset-password", max_age=3600)  # 1 hour validity
    except SignatureExpired:
        flash("The reset link has expired.", "danger")
        return redirect(url_for("forgot_password"))
    except BadSignature:
        flash("Invalid or broken reset link.", "danger")
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        new_password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        if new_password != confirm_password:
            flash("Passwords do not match.", "warning")
            return render_template('reset_password.html')
        if len(new_password) < 6:
            flash("Password must be at least 6 characters long.", "warning")
            return render_template('reset_password.html')

        hashed = bcrypt.generate_password_hash(new_password).decode()
        app.db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"password": hashed}})
        flash("Password reset successful. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html")


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        # You can store in DB, or print for now:
        print(f"Message from {name} ({email}): {message}")
        flash("Thanks for reaching out! We'll get back to you shortly.", "success")
        return redirect(url_for('contact'))
    return render_template('contact.html')

# ───── Student Dashboard ─────
@app.route('/student/dashboard')
@login_required
@role_required("student")
def student_dashboard():
    return render_template("student_dashboard.html")

# ───── Instructor Dashboard ─────
@app.route('/instructor/dashboard')
@login_required
@role_required("instructor")
def instructor_dashboard():
    return render_template("instructor_dashboard.html")

# ───── Profile Routes ─────
@app.route('/profile')
@login_required
def profile():
    user_id = session.get("user_id")
    user = get_user_by_id(app.db, user_id)
    if not user:
        return redirect(url_for("auth.login"))
    return render_template("profile.html", user=user)

@app.route('/upload-profile-picture', methods=['POST'])
def upload_profile_picture():
    # Use consistent session key
    if 'user_id' not in session:
        flash("You must be logged in to upload a profile picture.", "warning")
        return redirect(url_for('auth.login'))

    file = request.files.get('profile_pic')
    if not file:
        flash("No file selected.", "danger")
        return redirect(url_for('profile'))

    filename = secure_filename(file.filename)
    if not filename:
        flash("Invalid file name.", "danger")
        return redirect(url_for('profile'))

    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(upload_path)

    user_id = session['user_id']  # ✅ Match the session key used above
    app.db.users.update_one(
        {'_id': ObjectId(user_id)},
        {'$set': {'profile_pic': filename}}
    )
    session['user_pic'] = filename
    flash("Profile picture updated successfully!", "success")
    return redirect(url_for('profile'))

@app.route("/profile/edit", methods=["GET", "POST"])
def edit_profile():
    if "user_id" not in session:
        flash("Please log in first", "warning")
        return redirect(url_for("auth.login"))

    db = app.db
    user = db.users.find_one({"_id": ObjectId(session["user_id"])})

    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        new_password = request.form.get("password", "")

        update_fields = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email
        }

        if new_password:
            update_fields["password"] = app.bcrypt.generate_password_hash(new_password).decode()

        db.users.update_one({"_id": user["_id"]}, {"$set": update_fields})
        flash("Profile updated successfully", "success")
        session["user_name"] = first_name
        return redirect(url_for("profile"))

    return render_template("edit_profile.html", user=user)

# ───── Other Routes ─────
@app.route('/')
def home():
    return render_template("home.html")

@app.route('/about')
def about():
    return render_template("about.html")

def load_courses():
    try:
        with open('data/courses.json', 'r') as file:
            return json.load(file)
    except Exception as e:
        print("Error loading courses:", e)
        return []



@app.route("/courses")
@login_required
def courses():
    courses = list(app.db.courses.find())

    return render_template("courses.html", courses=courses)


@app.route("/course/<slug>")
@login_required
def course_detail(slug):
    courses = load_courses()
    course = next((c for c in courses if c["slug"] == slug), None)
    if not course:
        return "Course not found", 404
    return render_template("course_detail.html", course=course)

@app.route("/enroll/<slug>")
@login_required
def enroll(slug):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    # Lookup course by slug
    course = current_app.db.courses.find_one({"slug": slug})
    if not course:
        return "Course not found", 404

    course_id = course["_id"]

    # Enroll using your model
    enroll_student(current_app.db, user_id, course_id)

    return redirect(url_for('study_course', slug=slug))
     

@app.route("/study/<slug>")
@login_required
def study_course(slug):
    user_id = session.get('user_id')
    enrollment = enrollments_collection.find_one({
        "user_id": user_id,
        "course_slug": slug
    })

    if not enrollment:
        return redirect(url_for('courses'))

    course = get_enrollments_by_course(slug)
    if not course:
        return "Course not found", 404

    return render_template("study.html", course=course, enrollment=enrollment)  

@app.route("/complete/<slug>", methods=["POST"])
@login_required
def complete_course(slug):
    user_id = session.get('user_id')
    enrollment = enrollments_collection.find_one({
        "user_id": user_id,
        "course_slug": slug
    })

    if not enrollment:
        return redirect(url_for('courses'))

    enrollments_collection.update_one(
        {"_id": enrollment["_id"]},
        {"$set": {"status": "completed", "progress": 100}}
    )

    flash("Congratulations! You have completed the course.", "success")
    return redirect(url_for('study_course', slug=slug))      



# ───── Run Server ─────
if __name__ == '__main__':
    app.run(debug=True)