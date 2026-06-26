from functools import wraps
from flask import abort
from flask_login import current_user

def role_required(*roles):
    """
    Decorator to enforce Role-Based Access Control (RBAC).
    Restricts access to users belonging to any of the specified roles.
    Aborts with a 403 Forbidden error if unauthorized, or 401 if unauthenticated.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator
