from bson import ObjectId
from datetime import datetime

def create_course(db, title, description, instructor_id, image):
    # Fetch instructor details from users collection
    instructor = db.users.find_one({"_id": ObjectId(instructor_id)})

    if instructor:
        instructor_name = f"{instructor.get('firstName', '')} {instructor.get('lastName', '')}"
    else:
        instructor_name = "Unknown"

    course = {
        "title": title,
        "description": description,
        "instructor_id": ObjectId(instructor_id),
        "instructor_name": instructor_name,  # ✅ Save instructor name directly
        "image": image,
        "slug": title.lower().replace(" ", "-"),
        "students": [],
        "created_at": datetime.now()
    }

    return db.courses.insert_one(course)