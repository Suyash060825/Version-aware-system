import os
os.environ["FLASK_ENV"] = "development"
from app import create_app
from models import db, User

app = create_app()
with app.app_context():
    for u in User.query.all():
        dept_name = u.department.name if u.department else ""
        print(f"User: {u.email}, Role: {u.role}, Dept: {dept_name}")
