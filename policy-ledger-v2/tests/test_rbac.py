import pytest
from app import create_app
from models import db, User, UserRole

@pytest.fixture
def client():
    app = create_app("testing")
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()

def create_user(role, email="test@example.com"):
    user = User(email=email, role=role, name="Test User", password_hash="hash")
    db.session.add(user)
    db.session.commit()
    return user

def login(client, user):
    resp = client.post("/auth/login", data={"email": user.email, "password": "password"})
    if resp.status_code not in (200, 302):
        print(resp.data)
    return resp

def test_admin_route_requires_admin(client):
    # Not logged in
    res = client.get("/admin/users")
    assert res.status_code == 302 # redirect to login
    
    # Employee login
    employee = create_user(UserRole.EMPLOYEE, "emp@example.com")
    employee.set_password("password")
    db.session.commit()
    login(client, employee)
    
    res = client.get("/admin/users")
    assert res.status_code == 403
    
    # Admin login
    client.get("/auth/logout")
    admin = create_user(UserRole.ADMIN, "admin@example.com")
    admin.set_password("password")
    db.session.commit()
    login(client, admin)
    
    res = client.get("/admin/users")
    assert res.status_code == 200

def test_hr_route_access(client):
    employee = create_user(UserRole.EMPLOYEE, "emp2@example.com")
    employee.set_password("password")
    hr = create_user(UserRole.HR, "hr@example.com")
    hr.set_password("password")
    db.session.commit()
    
    # Employee cannot access HR features (e.g. policy list)
    client.get("/auth/logout")
    login(client, employee)
    res = client.get("/admin/policies")
    assert res.status_code == 403
    
    # HR can access policy list
    client.get("/auth/logout")
    login(client, hr)
    res = client.get("/admin/policies")
    assert res.status_code == 200
