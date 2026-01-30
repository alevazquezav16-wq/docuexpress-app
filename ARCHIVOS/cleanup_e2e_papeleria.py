import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ARCHIVOS.app import create_app, db
from ARCHIVOS.models import User, Papeleria

app = create_app()
with app.app_context():
    username = "admin"
    papeleria_nombre = "Papelería E2E Test"
    user = User.query.filter_by(username=username).first()
    if user:
        papelerias = Papeleria.query.filter_by(nombre=papeleria_nombre, user_id=user.id).all()
        for pap in papelerias:
            db.session.delete(pap)
        db.session.commit()
        print(f"✅ Papelería de test eliminada para usuario {username}")
    else:
        print(f"ℹ️ Usuario admin no existe, no se eliminó papelería de test.")
