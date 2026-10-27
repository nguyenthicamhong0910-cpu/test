import csv
import io
import os
from datetime import datetime, date
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, Response, abort
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("COOKIE_SECURE", "true").lower() == "true"
app.config["REMEMBER_COOKIE_HTTPONLY"] = True
app.config["WTF_CSRF_TIME_LIMIT"] = 3600

if not app.config["SECRET_KEY"] or not app.config["SQLALCHEMY_DATABASE_URI"]:
    # Fail closed: do not run with an insecure development secret or local-only DB by accident.
    if os.environ.get("ALLOW_LOCAL_DEV", "false").lower() != "true":
        raise RuntimeError("Set SECRET_KEY and DATABASE_URL environment variables before starting.")

db = SQLAlchemy(app)
csrf = CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Vui lòng đăng nhập để tiếp tục."

UNITS = {
    "tinh": "Tỉnh hội Tây Ninh",
    "myyen": "Hội CCB xã Mỹ Yên",
    "benluc": "Hội CCB xã Bến Lức",
    "tanninh": "Hội CCB phường Tân Ninh",
}

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # province_admin or unit_staff
    unit_id = db.Column(db.String(30), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def get_id(self):
        return str(self.id)

class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(160), nullable=False, index=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    unit_id = db.Column(db.String(30), nullable=False, index=True)
    joined_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(30), nullable=False, default="Đang sinh hoạt")
    address = db.Column(db.String(300), nullable=True)
    notes = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    action = db.Column(db.String(80), nullable=False)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.String(80), nullable=True)
    details = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    username = db.relationship("User", lazy="joined")

@login_manager.user_loader
def load_user(user_id):
    try:
        user = db.session.get(User, int(user_id))
        return user if user and user.active else None
    except (ValueError, TypeError):
        return None

@app.before_request
def enforce_config_and_session():
    # A production deployment must use HTTPS and a long random SECRET_KEY.
    pass

def is_province():
    return current_user.is_authenticated and current_user.role == "province_admin" and current_user.unit_id == "tinh"

def scoped_members():
    q = Member.query
    if not is_province():
        q = q.filter_by(unit_id=current_user.unit_id)
    return q

def audit(action, entity_type, entity_id=None, details=None):
    db.session.add(AuditLog(user_id=current_user.id, action=action, entity_type=entity_type,
                            entity_id=str(entity_id) if entity_id is not None else None,
                            details=(details or "")[:500]))

def parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and user.active and check_password_hash(user.password_hash, password):
            login_user(user)
            audit("login", "session", details="Đăng nhập thành công")
            db.session.commit()
            return redirect(url_for("dashboard"))
        flash("Tên đăng nhập hoặc mật khẩu không đúng.", "error")
    return render_template("login.html")

@app.route("/logout", methods=["POST"])
@login_required
def logout():
    audit("logout", "session", details="Đăng xuất")
    db.session.commit()
    logout_user()
    return redirect(url_for("login"))

@app.route("/")
@login_required
def dashboard():
    q = scoped_members()
    total = q.count()
    active = q.filter_by(status="Đang sinh hoạt").count()
    unit_ids = [current_user.unit_id] if not is_province() else ["myyen", "benluc", "tanninh"]
    rows = []
    for uid in unit_ids:
        unit_q = Member.query.filter_by(unit_id=uid)
        rows.append({"id": uid, "name": UNITS[uid], "total": unit_q.count(),
                     "active": unit_q.filter_by(status="Đang sinh hoạt").count(),
                     "inactive": unit_q.filter_by(status="Ngừng sinh hoạt").count()})
    return render_template("dashboard.html", total=total, active=active, rows=rows,
                           is_province=is_province(), unit_name=UNITS.get(current_user.unit_id, current_user.unit_id))

@app.route("/members")
@login_required
def members():
    q = scoped_members()
    term = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    unit_id = request.args.get("unit_id", "").strip()
    if term:
        like = f"%{term}%"
        q = q.filter(db.or_(Member.full_name.ilike(like), Member.code.ilike(like)))
    if status in ("Đang sinh hoạt", "Ngừng sinh hoạt"):
        q = q.filter_by(status=status)
    if is_province() and unit_id in ("myyen", "benluc", "tanninh"):
        q = q.filter_by(unit_id=unit_id)
    rows = q.order_by(Member.full_name.asc()).limit(2000).all()
    return render_template("members.html", members=rows, is_province=is_province(),
                           units=UNITS, selected_unit=unit_id, q=term, status=status,
                           unit_name=UNITS.get(current_user.unit_id, current_user.unit_id))

@app.route("/members/new", methods=["GET", "POST"])
@login_required
def member_new():
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        name = request.form.get("full_name", "").strip()
        unit_id = request.form.get("unit_id", "").strip()
        status = request.form.get("status", "Đang sinh hoạt")
        if not is_province():
            unit_id = current_user.unit_id
        if not code or not name or unit_id not in UNITS or unit_id == "tinh":
            flash("Vui lòng nhập mã, họ tên và chọn đơn vị cơ sở hợp lệ.", "error")
        elif status not in ("Đang sinh hoạt", "Ngừng sinh hoạt"):
            flash("Trạng thái không hợp lệ.", "error")
        elif Member.query.filter_by(code=code).first():
            flash("Mã hội viên đã tồn tại.", "error")
        else:
            m = Member(code=code, full_name=name, unit_id=unit_id,
                       date_of_birth=parse_date(request.form.get("date_of_birth")),
                       joined_date=parse_date(request.form.get("joined_date")),
                       status=status, address=request.form.get("address", "").strip()[:300],
                       notes=request.form.get("notes", "").strip()[:500])
            db.session.add(m)
            db.session.flush()
            audit("create", "member", m.id, f"Tạo hồ sơ {m.code}")
            db.session.commit()
            flash("Đã thêm hồ sơ hội viên.", "success")
            return redirect(url_for("members"))
    return render_template("member_form.html", member=None, is_province=is_province(),
                           units={k:v for k,v in UNITS.items() if k != "tinh"},
                           unit_name=UNITS.get(current_user.unit_id, current_user.unit_id))

@app.route("/members/<int:member_id>/edit", methods=["GET", "POST"])
@login_required
def member_edit(member_id):
    m = scoped_members().filter_by(id=member_id).first_or_404()
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        name = request.form.get("full_name", "").strip()
        unit_id = request.form.get("unit_id", "").strip() if is_province() else current_user.unit_id
        status = request.form.get("status", "")
        duplicate = Member.query.filter(Member.code == code, Member.id != m.id).first()
        if not code or not name or unit_id not in UNITS or unit_id == "tinh" or duplicate or status not in ("Đang sinh hoạt", "Ngừng sinh hoạt"):
            flash("Dữ liệu không hợp lệ, mã bị trùng hoặc đơn vị không hợp lệ.", "error")
        else:
            old_unit = m.unit_id
            m.code, m.full_name, m.unit_id = code, name, unit_id
            m.date_of_birth = parse_date(request.form.get("date_of_birth"))
            m.joined_date = parse_date(request.form.get("joined_date"))
            m.status = status
            m.address = request.form.get("address", "").strip()[:300]
            m.notes = request.form.get("notes", "").strip()[:500]
            audit("update", "member", m.id, f"Cập nhật hồ sơ {m.code}; đơn vị trước: {old_unit}")
            db.session.commit()
            flash("Đã cập nhật hồ sơ.", "success")
            return redirect(url_for("members"))
    return render_template("member_form.html", member=m, is_province=is_province(),
                           units={k:v for k,v in UNITS.items() if k != "tinh"},
                           unit_name=UNITS.get(current_user.unit_id, current_user.unit_id))

@app.route("/members/<int:member_id>/delete", methods=["POST"])
@login_required
def member_delete(member_id):
    m = scoped_members().filter_by(id=member_id).first_or_404()
    code = m.code
    audit("delete", "member", m.id, f"Xóa hồ sơ {code}")
    db.session.delete(m)
    db.session.commit()
    flash("Đã xóa hồ sơ.", "success")
    return redirect(url_for("members"))

@app.route("/export.csv")
@login_required
def export_csv():
    q = scoped_members().order_by(Member.full_name.asc())
    if is_province():
        uid = request.args.get("unit_id", "")
        if uid in ("myyen", "benluc", "tanninh"):
            q = q.filter_by(unit_id=uid)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Mã hội viên", "Họ và tên", "Ngày sinh", "Đơn vị", "Ngày vào Hội", "Trạng thái", "Địa chỉ", "Ghi chú"])
    for m in q.limit(10000).all():
        writer.writerow([m.code, m.full_name, m.date_of_birth or "", UNITS.get(m.unit_id, m.unit_id),
                         m.joined_date or "", m.status, m.address or "", m.notes or ""])
    audit("export", "member", details="Xuất danh sách CSV")
    db.session.commit()
    data = "\ufeff" + output.getvalue()
    return Response(data, mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=hoi_vien_ccb.csv"})

@app.route("/audit")
@login_required
def audit_view():
    if not is_province():
        abort(403)
    rows = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(500).all()
    return render_template("audit.html", rows=rows, unit_name=UNITS[current_user.unit_id])

@app.errorhandler(403)
def forbidden(_):
    return render_template("error.html", message="Bạn không có quyền truy cập chức năng này."), 403

@app.errorhandler(404)
def not_found(_):
    return render_template("error.html", message="Không tìm thấy hồ sơ hoặc trang yêu cầu."), 404

if __name__ == "__main__":
    if os.environ.get("ALLOW_LOCAL_DEV", "false").lower() != "true":
        raise RuntimeError("Use a production WSGI server (gunicorn), not Flask's development server.")
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=False)
