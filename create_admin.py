from app import app
from models import db, User
from werkzeug.security import generate_password_hash


with app.app_context():
    # Create the database tables if they don't exist
    db.create_all()

    # Check if an admin user exists
    from models import User
    admin_exists = User.query.filter_by(role='admin').first()
    if not admin_exists:
        from werkzeug.security import generate_password_hash
        username = 'admin'  # Replace with desired username
        password = '123'  # Replace with desired password
        name = 'Admin Name'          # Replace with the admin's name

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password, role='admin')
        db.session.add(new_user)
        db.session.commit()
        print('Admin user created successfully!')
    else:
        print('Admin user already exists.')