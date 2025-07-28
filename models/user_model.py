from bson.objectid import ObjectId




# ─────────────────────────────────────
# FIND USER BY EMAIL
# ─────────────────────────────────────
def find_user_by_email(db, email: str):
    return db.users.find_one({"email": email})


# ─────────────────────────────────────
# CREATE USER
# ─────────────────────────────────────
def create_user(db, first_name: str, last_name: str, email: str, password_hash: str, role: str):
    user = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "password": password_hash,
        "role": role 
    }
    result = db.users.insert_one(user)
    return result.inserted_id


# ─────────────────────────────────────
# GET USER BY ID
# ─────────────────────────────────────
def get_user_by_id(db, user_id: str):
    return db.users.find_one({"_id": ObjectId(user_id)})