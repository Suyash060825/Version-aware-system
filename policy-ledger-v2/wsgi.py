import os
from app import create_app

env = os.environ.get("FLASK_ENV", "production")
application = create_app(env)
