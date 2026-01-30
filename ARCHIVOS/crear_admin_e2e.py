import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ARCHIVOS.app import create_app
from ARCHIVOS.models import db, User

app = create_app()
with app.app_context():
    username = "admin"
    password = "admin123"
    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(username=username)
        user.set_password(password)
        user.role = "admin"
        db.session.add(user)
        db.session.commit()
        print(f"✅ Usuario admin creado para E2E: {username}/{password}")
    else:
        print(f"ℹ️ Usuario admin ya existe: {username}")
