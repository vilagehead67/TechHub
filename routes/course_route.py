from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from werkzeug.utils import secure_filename
from functools import wraps
import os
from bson import ObjectId
from datetime import datetime
from jinja2 import TemplateNotFound

from models.enrollment_model import enroll_student, get_enrollments_by_course
from utils.decorators import login_required
from models.course_model import create_course  # Optional use
course_routes = Blueprint('course_routes', __name__)

# ✅ Restrict access to instructors
def instructor_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Login required", "warning")
            return redirect(url_for("auth.login"))
        if session.get("user_role") != "instructor":
            flash("You’re not authorized", "danger")
            return redirect(url_for("main_routes.home"))
        return view_func(*args, **kwargs)
    return wrapper


# ✅ Create Course (Instructor only)
@course_routes.route("/create-course", methods=["GET", "POST"])
@instructor_required
def create_course_route():
    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        image = request.files["image"]

        # Handle image
        if image and image.filename != "":
            filename = secure_filename(image.filename)
            image_path = os.path.join(current_app.root_path, "static", "images", filename)
            image.save(image_path)
        else:
            filename = "default_course.jpg"

        # Get instructor details from session and database
        instructor_id = session.get("user_id")  # safer than session["user_id"]

        user = current_app.db.users.find_one({"_id": ObjectId(instructor_id)})
        if user:
            first_name = user.get("first_name", "").strip()
            last_name = user.get("last_name", "").strip()
            instructor_name = f"{first_name} {last_name}".strip()
        else:
            instructor_name = "Unknown"

        # Slug for URL
        slug = title.lower().replace(" ", "-")

        # Final course document
        course = {
            "title": title,
            "description": description,
            "instructor_id": ObjectId(instructor_id),
            "instructor_name": instructor_name,  # ✅ now it's valid
            "image": filename,
            "slug": slug,
            "students": [],
            "created_at": datetime.now()
        }

        # Save to DB
        current_app.db.courses.insert_one(course)
        flash("Course created successfully!", "success")
        return redirect(url_for("instructor_dashboard"))

    return render_template("create_course.html", instructor_name=session.get("user_name", "Instructor"))





# ✅ Enroll in course
@course_routes.route("/enroll/<slug>", methods=["POST"])
@login_required
def enroll(slug):
    student_id = session.get("user_id")  # student ID stored in session

    # Find the course by slug
    course = current_app.db.courses.find_one({"slug": slug})
    if not course:
        flash("Course not found.", "danger")
        return redirect(url_for("course_routes.courses"))

    course_id = str(course["_id"])

    # Check enrollment and enroll
    success = enroll_student(current_app.db, student_id, course_id)
    if success:
        flash("Enrolled successfully!", "success")
    else:
        flash("You are already enrolled.", "info")

    return redirect(url_for("course_routes.course_detail", slug=slug))


@course_routes.route("/courses")
@login_required
def courses():
    user_id = session.get("user_id")
    role = session.get("user_role")

    courses = list(current_app.db.courses.find())

    enrolled_course_ids = []
    if role == "student":
        enrollments = list(current_app.db.enrollments.find({"student_id": ObjectId(user_id)}))
        enrolled_course_ids = [enr["course_id"] for enr in enrollments]

    return render_template(
        "courses.html",
        courses=courses,
        enrolled_course_ids=enrolled_course_ids
    )




# ✅ Instructors view students enrolled in a course
@course_routes.route("/enrolled-students/<course_id>")
@instructor_required
def enrolled_students(course_id):
    db = current_app.db
    enrollments = get_enrollments_by_course(db, course_id)

    student_ids = [ObjectId(e["student_id"]) for e in enrollments]
    students = list(db.users.find({"_id": {"$in": student_ids}}))

    enrollment_map = {str(e["student_id"]): e["enrolled_at"] for e in enrollments}

    enriched_students = []
    for student in students:
        student_id_str = str(student["_id"])
        full_name = f"{student.get('first_name', '')} {student.get('last_name', '')}".strip()
        enriched_students.append({
            "full_name": full_name,
            "email": student.get("email", "N/A"),
            "enrolled_at": enrollment_map.get(student_id_str)
        })

    course = db.courses.find_one({"_id": ObjectId(course_id)})

    return render_template("enrolled_students.html", students=enriched_students, course=course)




@course_routes.route("/instructor/dashboard")
@instructor_required
def instructor_dashboard():
    instructor_id = session.get("user_id")
    courses = list(current_app.db.courses.find({"instructor_id": instructor_id}))
    return render_template("instructor_dashboard.html", courses=courses)

@course_routes.route("/my-courses")
@login_required
def my_courses():
    student_id = session.get("user_id")
    enrollments = list(current_app.db.enrollments.find({
        "student_id": ObjectId(student_id)
    }))

    course_ids = [enrollment["course_id"] for enrollment in enrollments]
    courses = list(current_app.db.courses.find({
        "_id": {"$in": course_ids}
    }))

    # Map course_id to enrollment for easy lookup
    enrollment_map = {str(e["course_id"]): e for e in enrollments}

    enrolled_courses = []
    for course in courses:
        course_id_str = str(course["_id"])
        course["completed"] = enrollment_map[course_id_str].get("completed", False)
        course["slug"] = course.get("slug", "")  # Ensure slug is passed to the template
        enrolled_courses.append(course)

    return render_template("my_courses.html", courses=enrolled_courses)





@course_routes.route("/course/<slug>")
@login_required
def course_detail(slug):
    course = current_app.db.courses.find_one({"slug": slug})
    if not course:
        return "Course not found", 404

    # Check if the logged-in user is enrolled in this course
    user_id = session.get("user_id")
    is_enrolled = current_app.db.enrollments.find_one({
        "student_id": user_id,
        "course_id": course["_id"]
    })

    return render_template("course_detail.html", course=course, is_enrolled=bool(is_enrolled))


@course_routes.route("/study/<slug>")
@login_required
def study(slug):
    user_id = session.get("user_id")

    # 1. Get the course by slug
    course = current_app.db.courses.find_one({"slug": slug})
    if not course:
        return "Course not found", 404

    # 2. Check if the user is enrolled
    enrollment = current_app.db.enrollments.find_one({
        "student_id": ObjectId(user_id),
        "course_id": course["_id"]
    })

    if not enrollment:
        # Not enrolled
        return redirect(url_for("my_courses") + "?error=You must enroll in the course to study it.")

    # 3. If enrolled, continue to render the course page
    progress = enrollment.get("progress", [])
    return render_template("courses/{}.html".format(slug), course=course, progress=progress)






