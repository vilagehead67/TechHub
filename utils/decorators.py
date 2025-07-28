from functools import wraps
from flask import session, redirect, url_for, flash

def role_required(role):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                flash("You must be logged in.", "warning")
                return redirect(url_for("auth.login"))
            if session.get("user_role") != role:
                flash("You are not authorized to access this page.", "danger")
                return redirect(url_for("home"))
            return view_func(*args, **kwargs)
        return wrapper
    return decorator


    # ───── Auth Decorator ─────
def login_required(view_function):
    @wraps(view_function)
    def wrapper(*args, **kwargs):
        if 'user' not in session:
            flash("You must be logged in to access this page.", "warning")
            return redirect(url_for('auth.login'))
        return view_function(*args, **kwargs)
    return wrapper

 
