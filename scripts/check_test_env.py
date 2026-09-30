from app import create_app
app = create_app('testing')
print("Testing DB:", app.config.get('SQLALCHEMY_DATABASE_URI'))
print("Testing Redis:", app.config.get('REDIS_URL'))
