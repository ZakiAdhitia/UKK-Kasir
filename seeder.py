from werkzeug.security import generate_password_hash
from app import create_app
from app.models import db, Users

def seed_users():
    users = [
        {
            "username": "admin",
            "password": generate_password_hash("123"),
            "role": "admin"
        },
        {
            "username": "petugas",
            "password": generate_password_hash("123"),
            "role": "petugas"
        }
    ]

    for user_data in users:
        existing_user = Users.query.filter_by(username=user_data['username']).first()
        if not existing_user:
            user = Users(**user_data)
            db.session.add(user)
    
    db.session.commit()
    print("Seeder users berhasil dijalankan.")

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        seed_users()
