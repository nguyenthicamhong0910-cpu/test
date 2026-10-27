"""Run once after deploying and creating tables. Set INITIAL_* environment variables first."""
import os
from app import app, db, User
from werkzeug.security import generate_password_hash

ACCOUNT_SPECS = [
    ("tinh1", "province_admin", "tinh", "INITIAL_TINH1_PASSWORD"),
    ("tinh2", "province_admin", "tinh", "INITIAL_TINH2_PASSWORD"),
    ("tinh3", "province_admin", "tinh", "INITIAL_TINH3_PASSWORD"),
    ("myyen", "unit_staff", "myyen", "INITIAL_MYYEN_PASSWORD"),
    ("benluc", "unit_staff", "benluc", "INITIAL_BENLUC_PASSWORD"),
    ("tanninh", "unit_staff", "tanninh", "INITIAL_TANNINH_PASSWORD"),
]

with app.app_context():
    db.create_all()
    missing = [env for _, _, _, env in ACCOUNT_SPECS if not os.environ.get(env)]
    if missing:
        raise SystemExit("Missing password environment variables: " + ", ".join(missing))
    for username, role, unit_id, env_name in ACCOUNT_SPECS:
        if User.query.filter_by(username=username).first():
            print(f"Skip existing account: {username}")
            continue
        password = os.environ[env_name]
        if len(password) < 14:
            raise SystemExit(f"{env_name} must be at least 14 characters long.")
        db.session.add(User(username=username, role=role, unit_id=unit_id,
                            password_hash=generate_password_hash(password), active=True))
    db.session.commit()
    print("Account seeding complete. Deliver initial passwords to authorized users securely.")
