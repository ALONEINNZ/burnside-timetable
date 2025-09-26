# ------------------- IMPORTS & CONFIG -------------------
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
    abort,
    jsonify,
)
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
from functools import wraps
import colorama
import sqlite3
import os
import csv
from pathlib import Path
import random


# ------------------- INITIALIZATION -------------------


app = Flask(__name__)
colorama.init(autoreset=True)
load_dotenv(Path(".env"))
key = os.getenv("KEY")
app.secret_key = key
app.config.update(
    MAIL_SERVER="smtp.gmail.com",
    MAIL_PORT=587,
    MAIL_USERNAME=os.getenv("USERNAME"),
    MAIL_PASSWORD=os.getenv("PASSWORD"),
    MAIL_USE_TLS=True,
    MAIL_USE_SSL=False,
)
mail = Mail(app)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "main.db")
app.config["UPLOAD_FOLDER"] = os.path.join(BASE_DIR, "static/images")
app.config["DATA_FOLDER"] = os.path.join(BASE_DIR, "static/data")
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["DATA_FOLDER"], exist_ok=True)
if not os.path.exists(DB_PATH):
    open(DB_PATH, "a").close()

# ------------------- CONSTANTS -------------------
SCHOOL_EMAIL_DOMAIN = "@burnside.school.nz"
ADMIN_CODES = ["22298"]


# ------------------- DECORATORS -------------------
def login_required(f):
    """Restrict access to logged-in users."""

    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated


# ------------------- EMAIL -------------------
def send_email(user_email, key):
    """Send verification email to Burnside students only."""
    if not user_email.lower().endswith(SCHOOL_EMAIL_DOMAIN):
        flash("Please use your Burnside school email!")
        return
    msg = Message(
        subject="Verify your email",
        sender=app.config["MAIL_USERNAME"],
        recipients=[user_email],
        body=f"Confirm your email by clicking: http://127.0.0.1:5000/verify/{key}",
    )
    mail.send(msg)


# ------------------- DATABASE FUNCTIONS -------------------
def add_class(name, years, is_mandatory=False, prerequisites=None):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        for year in years:
            cursor.execute(
                "SELECT id FROM classes WHERE name=? AND year=?", (name, year)
            )
            existing = cursor.fetchone()
            if existing:
                cursor.execute(
                    "UPDATE classes SET name=?, year=?, is_mandatory=?, prerequisites=? WHERE id=?",
                    (name, year, is_mandatory, prerequisites, existing[0]),
                )
            else:
                cursor.execute(
                    "INSERT INTO classes(name, year, is_mandatory, prerequisites) VALUES(?,?,?,?)",
                    (name, year, is_mandatory, prerequisites),
                )
        conn.commit()


def add_classes_from_file(file_name):
    with open(file_name, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        for line in reader:
            name, years_range, is_mandatory, prerequisites = line
            years = (
                list(
                    range(
                        int(years_range.split("-")[0]),
                        int(years_range.split("-")[1]) + 1,
                    )
                )
                if "-" in years_range
                else [int(years_range)]
            )
            add_class(
                name, years, is_mandatory.strip().lower() == "true", prerequisites
            )


def add_job(name, salary_avg, area):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM jobs WHERE name=?", (name,))
        existing = cursor.fetchone()
        if existing:
            cursor.execute(
                "UPDATE jobs SET salary_avg=?, area=? WHERE id=?",
                (salary_avg, area, existing[0]),
            )
        else:
            cursor.execute(
                "INSERT INTO jobs(name, salary_avg, area) VALUES(?,?,?)",
                (name, salary_avg, area),
            )
        conn.commit()


def add_jobs_from_file(file_name):
    with open(file_name, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("name", "").strip()
            avg_salary = row.get("avg_salary", "0").strip()
            area = row.get("area", "").strip()
            if not name or not avg_salary:
                continue
            try:
                avg_salary = int(avg_salary)
            except:
                avg_salary = 0
            add_job(name, avg_salary, area)


def add_job_classes_from_file(file_name):
    with open(file_name, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            class_id = row.get("class_id")
            jobs_str = row.get("jobs", "")
            if not class_id or not jobs_str:
                continue
            job_names = [j.strip() for j in jobs_str.split(";") if j.strip()]
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                for job_name in job_names:
                    cursor.execute(
                        "SELECT id FROM jobs WHERE LOWER(name)=?", (job_name.lower(),)
                    )
                    job_row = cursor.fetchone()
                    if job_row:
                        job_id = job_row[0]
                        cursor.execute(
                            "INSERT OR IGNORE INTO job_classes(class_id, job_id) VALUES (?, ?)",
                            (class_id, job_id),
                        )
                conn.commit()


def add_all_high_school_classes_job_classes():
    file_path = os.path.join(app.config["DATA_FOLDER"], "all_high_school_classes.csv")
    add_job_classes_from_file(file_path)


# ------------------- ROUTES -------------------
@app.route("/")
def home():
    return render_template("home.html", header="Home")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    """User signup route with email verification."""
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


@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
    """User account route with profile picture upload."""
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
    """User login route with session management."""
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


@app.get("/admin")
@login_required
def admin():
    if session.get("code") not in ADMIN_CODES:
        abort(404)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id,name,year,is_mandatory,prerequisites FROM classes ORDER BY name, year"
        )
        classes = cursor.fetchall()
        subjects = []
        for c in classes:
            cursor.execute(
                "SELECT id,name FROM jobs WHERE id IN (SELECT job_id FROM job_classes WHERE class_id=?)",
                (c[0],),
            )
            jobs = cursor.fetchall()
            subjects.append(
                {
                    "id": c[0],
                    "name": c[1],
                    "year": c[2],
                    "is_mandatory": c[3],
                    "prerequisites": c[4],
                    "jobs": jobs,
                }
            )
        cursor.execute("SELECT id,name FROM jobs ORDER BY name")
        jobs = cursor.fetchall()
    return render_template(
        "admin.html", header="Admin", subjects=subjects, all_jobs=jobs
    )


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


@app.route("/import-job-classes")
@login_required
def import_job_classes():
    try:
        add_all_high_school_classes_job_classes()
        flash("Job-class relationships imported successfully!")
    except Exception as e:
        flash(f"Error importing job-class relationships: {e}")
    return redirect(url_for("admin"))


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


@app.route("/import-bulk-jobs")
@login_required
def import_bulk_jobs():
    file_path = os.path.join(app.config["DATA_FOLDER"], "jobs_bulk.csv")
    try:
        add_jobs_from_file(file_path)
        flash("400 jobs imported successfully!")
    except Exception as e:
        flash(f"Error importing jobs: {e}")
    return redirect(url_for("admin"))


# ------------------- SUBJECT ROUTES -------------------
@app.route("/subject")
def subject_selection():
    return render_template("subject_selection.html", header="Subject Selection")


@app.post("/add-job-to-class/<int:class_id>/<int:job_id>")
def add_job_to_class(class_id, job_id):
    if session.get("code") not in ADMIN_CODES:
        abort(404)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO job_classes(class_id, job_id) VALUES(?,?)",
            (class_id, job_id),
        )
    return redirect(url_for("admin"))


@app.post("/remove-job-from-class/<int:class_id>/<int:job_id>")
def remove_job_from_class(class_id, job_id):
    if session.get("code") not in ADMIN_CODES:
        abort(404)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "DELETE FROM job_classes WHERE class_id=? AND job_id=?", (class_id, job_id)
        )
    return redirect(url_for("admin"))


# ------------------- SEARCH -------------------
@app.route("/subject-search", methods=["POST"])
def subject_search():
    data = request.get_json()
    term = data.get("term", "").strip().lower()
    results = []

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Search classes
        cursor.execute(
            "SELECT id, name, year, is_mandatory FROM classes WHERE LOWER(name)=? OR LOWER(name) LIKE ? ORDER BY name",
            (term, f"%{term}%"),
        )
        classes = cursor.fetchall()
        for c in classes:
            cursor.execute(
                """
                SELECT j.id, j.name FROM jobs j
                JOIN job_classes jc ON jc.job_id = j.id
                WHERE jc.class_id = ?
            """,
                (c[0],),
            )
            jobs = cursor.fetchall()
            results.append(
                {
                    "type": "class",
                    "id": c[0],
                    "name": c[1],
                    "year": c[2],
                    "is_mandatory": bool(c[3]),
                    "jobs": [{"id": j[0], "name": j[1]} for j in jobs],
                }
            )

        # Search jobs
        cursor.execute(
            "SELECT id, name FROM jobs WHERE LOWER(name)=? OR LOWER(name) LIKE ? ORDER BY name",
            (term, f"%{term}%"),
        )
        jobs = cursor.fetchall()
        for j in jobs:
            cursor.execute(
                """
                SELECT c.id, c.name, c.year, c.is_mandatory FROM classes c
                JOIN job_classes jc ON jc.class_id = c.id
                WHERE jc.job_id = ?
            """,
                (j[0],),
            )
            classes_for_job = cursor.fetchall()
            results.append(
                {
                    "type": "job",
                    "id": j[0],
                    "name": j[1],
                    "classes": [
                        {
                            "id": c[0],
                            "name": c[1],
                            "year": c[2],
                            "is_mandatory": bool(c[3]),
                        }
                        for c in classes_for_job
                    ],
                }
            )

    if not results:
        return jsonify({"type": "none"})
    return jsonify(results[0])  # Return the first match so frontend displays something


# ------------------- CLASS/JOB BY ID -------------------
@app.route("/subject/<int:class_id>")
def subject_by_id(class_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, year, is_mandatory FROM classes WHERE id = ?", (class_id,)
        )
        class_ = cursor.fetchone()
        if not class_:
            return render_template("404.html"), 404
        cursor.execute(
            """
            SELECT j.id, j.name FROM jobs j
            JOIN job_classes jc ON jc.job_id = j.id
            WHERE jc.class_id = ?
        """,
            (class_id,),
        )
        jobs = cursor.fetchall()
    return render_template(
        "subject_selection.html",
        header="Subject Selection",
        selected_class={
            "id": class_[0],
            "name": class_[1],
            "year": class_[2],
            "is_mandatory": class_[3],
        },
        jobs=[{"id": j[0], "name": j[1]} for j in jobs],
    )


@app.route("/subject/job/<int:job_id>")
def subject_by_job_id(job_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM jobs WHERE id = ?", (job_id,))
        job = cursor.fetchone()
        if not job:
            return render_template("404.html"), 404
        cursor.execute(
            """
            SELECT c.id, c.name, c.year, c.is_mandatory FROM classes c
            JOIN job_classes jc ON jc.class_id = c.id
            WHERE jc.job_id = ?
            ORDER BY c.year
        """,
            (job_id,),
        )
        classes = cursor.fetchall()
    return render_template(
        "subject_selection.html",
        header="Subject Selection",
        selected_job={"id": job[0], "name": job[1]},
        classes=[
            {"id": c[0], "name": c[1], "year": c[2], "is_mandatory": c[3]}
            for c in classes
        ],
    )


@app.route("/class-suggestions")
def class_suggestions():
    term = request.args.get("term", "").strip().lower()
    suggestions = []

    if term:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            # Classes
            cursor.execute(
                "SELECT DISTINCT name FROM classes WHERE LOWER(name) LIKE ? ORDER BY name LIMIT 5",
                (f"%{term}%",),
            )
            suggestions += [row[0] for row in cursor.fetchall()]

            # Jobs
            cursor.execute(
                "SELECT DISTINCT name FROM jobs WHERE LOWER(name) LIKE ? ORDER BY name LIMIT 5",
                (f"%{term}%",),
            )
            suggestions += [row[0] for row in cursor.fetchall()]

    return jsonify(suggestions)


@app.route("/verify/<int:key>")
def verify(key):
    """Verify user email using the provided key."""
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


# ------------------- TEST ROUTE -------------------
@app.route("/test-boundary/<username>")
def test_boundary(username):
    """Test username length boundaries: 3-10 chars"""
    if not (3 <= len(username) <= 10):
        return f"Invalid username length ({len(username)}). Must be 3-10 chars.", 400
    return f"Username {username} OK!", 200


# ------------------- ERROR HANDLERS -------------------
@app.errorhandler(500)
def server_err(err):
    return render_template("500.html"), 500


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


@app.route("/search_doesnt_exist")
def search_not_found():
    return render_template("search_doesnt_exist.html"), 404


# ------------------- MAIN -------------------
if __name__ == "__main__":
    app.run(debug=True)
