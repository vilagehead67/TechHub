from flask import Blueprint, request, jsonify, session, redirect, url_for, flash, render_template, current_app

from models.user_model import find_user_by_email, create_user, get_user_by_id

auth_bp = Blueprint("auth", __name__, template_folder="../templates")

# ─────────────────────────────────────
# Helpers to get db and bcrypt from app
# ─────────────────────────────────────
def get_db():
    return current_app.db

def get_bcrypt():
    return current_app.bcrypt

# ─────────────────────────────────────
# REGISTER
# ─────────────────────────────────────
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template("register.html")

    # POST
    first_name = request.form.get('first_name', '').strip()
    last_name = request.form.get('last_name', '').strip()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    confirm_password = request.form.get('confirm_password', '')
    role = request.form.get('role', 'student')  # Default to student

    # Debug log
    print("Registration attempt:", first_name, last_name, email)

    # Validation
    if not all([first_name, last_name, email, password, confirm_password]):
        flash("All fields are required", "warning")
        return redirect(url_for("auth.register"))

    if '@' not in email:
        flash("Invalid email", "warning")
        return redirect(url_for("auth.register"))

    if password != confirm_password:
        flash("Passwords do not match", "warning")
        return redirect(url_for("auth.register"))

    if find_user_by_email(get_db(), email):
        flash("User already exists", "warning")
        return redirect(url_for("auth.register"))

    if len(password) < 6:
        flash("Password must be at least 6 characters", "warning")
        return redirect(url_for("auth.register"))

    # Hash password
    pw_hash = get_bcrypt().generate_password_hash(password).decode()

    # Save user
    user_id = create_user(get_db(), first_name, last_name, email, pw_hash, role)
    print("User created with ID:", user_id)

    flash("Registration successful. Please login.", "success")
    return redirect(url_for("auth.login"))

# ─────────────────────────────────────
# LOGIN
# ─────────────────────────────────────
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email")
    password = request.form.get("password")

    user = find_user_by_email(get_db(), email)
    if not user or not get_bcrypt().check_password_hash(user["password"], password):
        flash("Invalid credentials", "danger")
        return redirect(url_for("auth.login"))

    # ✅ Save a unified user object in session
    session["user"] = {
        "id": str(user["_id"]),
        "role": user["role"],
        "name": user["first_name"],
        "pic": user.get("profile_pic", "default.jpg")
    }

    # Optional: still keep the individual keys if older routes depend on them
    session["user_id"] = str(user["_id"])
    session["user_role"] = user["role"]
    session["user_name"] = user["first_name"]
    session["user_pic"] = user.get("profile_pic", "default.jpg")

    flash("Login successful!", "success")

    # ✅ Role-based redirect
    if user["role"] == "student":
        return redirect(url_for("student_dashboard"))
    elif user["role"] == "instructor":
        return redirect(url_for("instructor_dashboard"))
    else:
        return redirect(url_for("home"))



# ─────────────────────────────────────
# LOGOUT
# ─────────────────────────────────────
@auth_bp.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("You've been logged out.", "info")
    return redirect(url_for("home"))