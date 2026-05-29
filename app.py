from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "39b3bcf4572b17a73a7cac9182fc5fafd15c3c06819eae7778510ab0b6b6e129"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ---------------- MODELS ---------------- #

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    role = db.Column(db.String(20))   # student, hod, warden, gate
    department = db.Column(db.String(50))
    gender = db.Column(db.String(10))
    year = db.Column(db.String(10))
    room_no = db.Column(db.String(10))


class Leave(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer)
    from_date = db.Column(db.String(20))
    to_date = db.Column(db.String(20))
    reason = db.Column(db.String(200))

    hod_status = db.Column(db.String(20), default="Pending")
    warden_status = db.Column(db.String(20), default="Pending")

    out_marked = db.Column(db.Boolean, default=False)
    in_marked = db.Column(db.Boolean, default=False)


# ---------------- LOGIN ---------------- #

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["role"] = user.role

            if user.role == "student":
                return redirect("/student")
            elif user.role == "hod":
                return redirect("/hod")
            elif user.role == "warden":
                return redirect("/warden")
            else:
                return redirect("/gate")

        return "Invalid Credentials"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ---------------- STUDENT ---------------- #

@app.route("/student", methods=["GET", "POST"])
def student_dashboard():
    if session.get("role") != "student":
        return redirect("/")

    if request.method == "POST":
        leave = Leave(
            student_id=session["user_id"],
            from_date=request.form["from"],
            to_date=request.form["to"],
            reason=request.form["reason"]
        )
        db.session.add(leave)
        db.session.commit()

    leaves = Leave.query.filter_by(student_id=session["user_id"]).all()
    return render_template("student_dashboard.html", leaves=leaves)


# ---------------- HOD ---------------- #

@app.route("/hod", methods=["GET", "POST"])
def hod_dashboard():
    if session.get("role") != "hod":
        return redirect("/")

    if request.method == "POST":
        leave = Leave.query.get(request.form["leave_id"])
        leave.hod_status = request.form["action"]
        db.session.commit()

    leaves = Leave.query.filter_by(hod_status="Pending").all()
    return render_template("hod_dashboard.html", leaves=leaves)


# ---------------- WARDEN ---------------- #

@app.route("/warden", methods=["GET", "POST"])
def warden_dashboard():
    if session.get("role") != "warden":
        return redirect("/")

    if request.method == "POST":
        leave = Leave.query.get(request.form["leave_id"])
        leave.warden_status = request.form["action"]
        db.session.commit()

    leaves = Leave.query.filter_by(
        hod_status="Approved",
        warden_status="Pending"
    ).all()

    out_ids = [l.student_id for l in Leave.query.filter_by(out_marked=True)]
    present_students = User.query.filter_by(role="student").filter(
        ~User.id.in_(out_ids)
    ).all()

    return render_template(
        "warden_dashboard.html",
        leaves=leaves,
        present_students=present_students
    )


# ---------------- GATE ---------------- #

@app.route("/gate", methods=["GET", "POST"])
def gate_dashboard():
    if session.get("role") != "gate":
        return redirect("/")

    if request.method == "POST":
        leave = Leave.query.get(request.form["leave_id"])
        if request.form["action"] == "OUT":
            leave.out_marked = True
        else:
            leave.in_marked = True
        db.session.commit()

    leaves = Leave.query.filter_by(warden_status="Approved").all()
    return render_template("gate_dashboard.html", leaves=leaves)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)