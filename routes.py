from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
    abort,
)
from flask.cli import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
import colorama
import sqlite3
import os
from pathlib import Path
from flask_mail import Mail, Message
import random
from werkzeug.utils import secure_filename
from functools import wraps  # <-- ADDED
import csv
from flask import jsonify


colorama.init(autoreset=True)

# Load environment variables
dotenv_path = Path(".env")
load_dotenv(dotenv_path)

app = Flask(__name__)
app.secret_key = os.getenv("KEY")

app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USERNAME"] = os.getenv("USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("PASSWORD")
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USE_SSL"] = False

app.config["UPLOAD_FOLDER"] = "static/images/"
app.config["DATA_FOLDER"] = "static/data/"
mail = Mail(app)


# --- LOGIN REQUIRED DECORATOR ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


def send_email(user_email, key):
    msg = Message(
        subject="verify your email",
        sender=app.config["MAIL_USERNAME"],
        recipients=[user_email],
        body=f"confirm your email by clicking the link below! http://127.0.0.1:5000/verify/{key}",
    )
    mail.send(msg)


def add_class(name, years, is_mandatory=False, prerequisites=None):
    with sqlite3.connect("main.db") as conn:
        for year in years:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM classes WHERE name = ? AND year = ?",
                (name, year),
            )
            existing_class = cursor.fetchone()
            # If the class already exists, update it
            if existing_class is not None:
                sql = "UPDATE classes SET name = ?, year = ?, is_mandatory = ?, prerequisites = ? WHERE id = ?"
                cursor.execute(
                    sql, (name, year, is_mandatory, prerequisites, existing_class[0])
                )
                conn.commit()
            else:
                # if the class does not exist, add it
                sql = "INSERT INTO classes(name, year, is_mandatory, prerequisites) VALUES(?,?,?,?)"
                cursor.execute(sql, (name, year, is_mandatory, prerequisites))
                conn.commit()


def add_classes_from_file(file_name):
    with open(file_name, "r", newline="", encoding="utf-8") as file:
        csv_reader = csv.reader(file)  # Read the header lines
        # check for errors
        header = next(csv_reader)
        for line in csv_reader:
            name, years_range, is_mandatory, prerequisites = line
            if "-" in years_range:
                start_year, end_year = years_range.split("-")
                years = list(range(int(start_year), int(end_year) + 1))
            else:
                years = [int(years_range)]

            is_mandatory = is_mandatory.strip().lower() == "true"
            add_class(name, years, is_mandatory, prerequisites)


def add_job(name, salary_avg, area):
    with sqlite3.connect("main.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM jobs WHERE name = ?",
            (name,),
        )
        existing_job = cursor.fetchone()
        # If the job already exists, update it
        if existing_job is not None:
            sql = "UPDATE jobs SET salary_avg = ?, area = ? WHERE id = ?"
            cursor.execute(sql, (salary_avg, area, existing_job[0]))
            conn.commit()
        else:
            # if the job does not exist, add it
            sql = "INSERT INTO jobs(name, salary_avg, area) VALUES(?,?,?)"
            cursor.execute(sql, (name, salary_avg, area))
            conn.commit()


def add_jobs_from_file(file_name):
    with open(file_name, "r", newline="", encoding="utf-8") as file:
        csv_reader = csv.reader(file)  # Read the header lines
        # check for errors
        header = next(csv_reader)
        for line in csv_reader:
            name, avg_salary, area = line

            add_job(name, int(avg_salary), area)


@app.route("/")
def home():
    return render_template("home.html", header="Home")


@app.get("/admin")
@login_required
def admin():
    """Admin page to view and update classes and jobs."""
    if not session["code"].isdigit() or session["code"] == "22298":
        with sqlite3.connect("main.db") as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id,name,year,is_mandatory,prerequisites FROM classes ORDER BY name, year"
            )
            classes = cursor.fetchall()
        subjects = []
        for class_ in classes:
            class_ = list(class_)
            with sqlite3.connect("main.db") as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id,name FROM jobs WHERE id IN (SELECT job_id FROM job_classes WHERE class_id = ?)",
                    (class_[0],),
                )
                jobs = cursor.fetchall()
            subjects.append(
                {
                    "id": class_[0],
                    "name": class_[1],
                    "year": class_[2],
                    "is_mandatory": class_[3],
                    "prerequisites": class_[4],
                    "jobs": jobs,
                }
            )
        return render_template("admin.html", header="Admin", subjects=subjects)
    else:
        abort(404)


@app.post("/remove-job-from-class/<int:class_id>/<int:job_id>")
def remove_job_from_class(class_id, job_id):
    """Remove a job from a class."""
    if session["code"].isdigit() and session["code"] != "22298":
        abort(404)
    with sqlite3.connect("main.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM job_classes WHERE class_id = ? AND job_id = ?",
            (class_id, job_id),
        )
        conn.commit()
    return redirect(url_for("admin"))


@app.post("/update-classes")
def update_classes():
    """Update classes from uploaded CSV file."""
    if "file" not in request.files:
        flash("No file part")
        return redirect(request.url)

    file = request.files["file"]
    filename = secure_filename(file.filename)

    if filename and file and file.filename != "":
        file.save(os.path.join(app.config["DATA_FOLDER"], filename))
        add_classes_from_file(os.path.join(app.config["DATA_FOLDER"], filename))
        flash("Classes updated successfully!")
        return redirect(url_for("admin"))
    else:
        flash("No file selected")
        return redirect(request.url)


@app.post("/update-jobs")
def update_jobs():
    """Update jobs from uploaded CSV file."""
    if "file" not in request.files:
        flash("No file part")
        return redirect(request.url)

    file = request.files["file"]
    filename = secure_filename(file.filename)

    if filename and file and file.filename != "":
        file.save(os.path.join(app.config["DATA_FOLDER"], filename))
        add_jobs_from_file(os.path.join(app.config["DATA_FOLDER"], filename))
        flash("jobs updated successfully!")
        return redirect(url_for("admin"))
    else:
        flash("No file selected")
        return redirect(request.url)


@app.route("/test")
def test():
    return render_template("test.html", header="Test me")


@app.route("/pizza")
def pizza():
    conn = sqlite3.connect("pizza.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Pizza")
    pizzas = cursor.fetchall()
    conn.close()
    return render_template("pizzas.html", header="pizza", pizzas=pizzas)


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


@app.route("/search_doesnt_exist")
def search_not_found():
    return render_template("search_doesnt_exist.html"), 404


@app.errorhandler(500)
def server_err(err):
    return render_template("500.html"), 500


@app.route("/about")
def about():
    return render_template("about.html", header="About")


@app.route("/subject")
def subject_selection():
    return render_template("subject_selection.html", header="Subject Selection")


@app.route("/help")
def help():
    return render_template("help.html", header="Help")


@app.route("/technology")
def technology():
    return render_template("technology.html", header="tech")


@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
    """ User account route with profile picture upload."""
    if request.method == "GET":
        return render_template("account.html", header="account")

    if "file" not in request.files:
        flash("No file part")
        return redirect(request.url)

    file = request.files["file"]
    filename = secure_filename(file.filename)

    # Check if a file was selected and is not empty
    if filename and file and file.filename != "":
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        conn = sqlite3.connect("main.db")
        cursor = conn.cursor()
        sql = "UPDATE users SET pfp = ? WHERE username = ?"
        cursor.execute(sql, (filename, session["username"]))
        conn.commit()
        conn.close()

        session["pfp"] = filename
        return redirect(url_for("home"))
    else:
        flash("No file selected")
        return redirect(request.url)


@app.route("/login", methods=["GET", "POST"])
def login():
    """ User login route with session management."""
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("main.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user is None:
            error = "User not found or Not Verified."
        elif user[5] == 0:  # is_verified check
            error = "Not verified. Check your email!"
        elif check_password_hash(user[2], password):  # hashed password
            session["username"] = username
            session["pfp"] = user[6]  # pfp assumed at index 6
            session["code"] = user[4]
            return redirect(url_for("home"))
        else:
            error = "Incorrect password."

    return render_template("login.html", header="login", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    """ User signup route with email verification."""
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        email = request.form["email"]
        code = request.form["code"]

        if password != confirm_password:
            error = "Passwords don't match!"
        elif len(password) > 8:
            error = "password is too long!"
        elif not email.endswith("@burnside.school.nz") or email.split("@")[0] != code:
            error = "Invalid email — must be @burnside and match student ID."
        elif len(code) != 5 or not code.isdigit():
            error = "Invalid student ID"
        else:
            conn = sqlite3.connect("main.db")
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM users WHERE username = ? OR code = ?",
                (username, code),
            )
            existing_user = cursor.fetchone()

            if existing_user:
                error = "User already exists"
            elif len(username) > 10:
                error = "username too long"
            else:
                key = random.randint(1000000000, 1000000000000000000)
                hashed_password = generate_password_hash(password)
                sql = "INSERT INTO users(username, password, code, email, key, is_verified) VALUES(?,?,?,?,?,?)"
                cursor.execute(
                    sql, (username, hashed_password, code, email, key, False)
                )
                conn.commit()
                conn.close()
                send_email(email, key)
                return render_template(
                    "login.html", header="login", error="check your email."
                )
            conn.close()

    return render_template("signup.html", header="signup", error=error)


@app.route("/verify/<int:key>")
def verify(key):
    """ Verify user email using the provided key."""
    with sqlite3.connect("main.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE key = ?", (key,))
        user = cursor.fetchone()

    if user is not None:
        conn = sqlite3.connect("main.db")
        cursor = conn.cursor()
        sql = "UPDATE users SET is_verified = ? WHERE id = ?"
        cursor.execute(sql, (True, user[0]))
        conn.commit()
        conn.close()

    return render_template("login.html", header="login", error="you are verified")


@app.route("/subject-search", methods=["POST"])
def subject_search():
    data = request.get_json()
    term = data.get("term", "").strip().lower()
    results = {}

    with sqlite3.connect("main.db") as conn:
        cursor = conn.cursor()
        # Check if it's a job
        cursor.execute("SELECT id, name FROM jobs WHERE LOWER(name) LIKE ?", (f"%{term}%",))
        job = cursor.fetchone()
        if job:
            # Get all classes required for this job, including is_mandatory and year
            cursor.execute("""
                SELECT c.id, c.name, c.year, c.is_mandatory FROM classes c
                JOIN job_classes jc ON jc.class_id = c.id
                WHERE jc.job_id = ?
                ORDER BY c.year
            """, (job[0],))
            classes = cursor.fetchall()
            results = {
                "type": "job",
                "name": job[1],
                "classes": [
                    {
                        "id": c[0],
                        "name": c[1],
                        "year": c[2],
                        "is_mandatory": bool(c[3])
                    } for c in classes
                ]
            }
            return jsonify(results)

        # Check if it's a class
        cursor.execute("SELECT id, name FROM classes WHERE LOWER(name) LIKE ?", (f"%{term}%",))
        class_ = cursor.fetchone()
        if class_:
            # Get all jobs that require this class
            cursor.execute("""
                SELECT j.name FROM jobs j
                JOIN job_classes jc ON jc.job_id = j.id
                WHERE jc.class_id = ?
            """, (class_[0],))
            jobs = cursor.fetchall()
            results = {
                "type": "class",
                "name": class_[1],
                "jobs": [j[0] for j in jobs]
            }
            return jsonify(results)

    return jsonify({"type": "none"})


@app.route("/class-suggestions")
def class_suggestions():
    term = request.args.get("term", "").strip().lower()
    with sqlite3.connect("main.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM classes WHERE LOWER(name) LIKE ? ORDER BY name LIMIT 7",
            (f"%{term}%",),
        )
        suggestions = [row[0] for row in cursor.fetchall()]
    return jsonify(suggestions)


if __name__ == "__main__":
    app.run(debug=True)
