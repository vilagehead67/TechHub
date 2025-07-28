# models/enrollment_model.py
from bson import ObjectId
from datetime import datetime

def enroll_student(db, student_id, course_id):
    existing = db.enrollments.find_one({
        "student_id": ObjectId(student_id),
        "course_id": ObjectId(course_id)
    })
    if existing:
        return False  # Already enrolled

    db.enrollments.insert_one({
    "student_id": ObjectId(student_id),  # ✅ convert to ObjectId
    "course_id": ObjectId(course_id),
    "completed": False,
    "enrolled_at": datetime.now()
})

    # Optional: add student to course's "students" array
    db.courses.update_one(
        {"_id": ObjectId(course_id)},
        {"$addToSet": {"students": ObjectId(student_id)}}
    )
    return True

def get_enrollments_by_course(db, course_id):
    return list(db.enrollments.find({"course_id": ObjectId(course_id)}))