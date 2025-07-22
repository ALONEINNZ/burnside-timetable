from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask.cli import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
import colorama
import sqlite3
import os
from pathlib import Path
from flask_mail import Mail, Message
import random
from werkzeug.utils import secure_filename

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

mail = Mail(app)


def send_email(user_email, key):
    msg = Message(
        subject="verify your email",
        sender=app.config["MAIL_USERNAME"],
        recipients=[user_email],
        body=f"confirm your email by clicking the link below! http://127.0.0.1:5000/verify/{key}",
    )

    mail.send(msg)


@app.route("/")
def home():
    return render_template("home.html", header="Home")


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
<<<<<<< Updated upstream
    return render_template('404.html'), 404
=======
<<<<<<< HEAD
    return render_template("404.html"), 404
=======
    return render_template('404.html'), 404
>>>>>>> 1beba980d089ba837d4b55762503e955c0563dc2
>>>>>>> Stashed changes


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
def account():
    if request.method == "GET":
        return render_template("account.html", header="account")
    if "file" not in request.files:
        flash("no file part")
    file = request.files["file"]
    filename = secure_filename(file.filename)
    if filename != "":
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
    conn = sqlite3.connect("main.db")
    cursor = conn.cursor()
    sql = "UPDATE users SET pfp = ? WHERE id = ?"
    cursor.execute(sql, (filename, session["user_id"]))
    conn.commit()
    conn.close()
    session["pfp"] = filename
    return redirect(url_for("home"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("main.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
<<<<<<< Updated upstream
=======
<<<<<<< HEAD
        print(user[7])
        if user[7] == 0:
            error = "not verified check your email!"
            return render_template("login.html", header="login", error=error)
        if user and check_password_hash(user[2], password):
            session["username"] = username
            session["pfp"] = user[3]
            session["user_id"] = user[0]
            flash("You successfully logged in")
            return redirect(url_for("home"))
        error = "Invalid username/password"
    return render_template("login.html", header="login", error=error)
=======
>>>>>>> 1beba980d089ba837d4b55762503e955c0563dc2
>>>>>>> Stashed changes

        if user is None:
            error = "User not found or Not Verified."
        elif user[5] == 0:  # Assuming index 5 is is_verified (fix if needed)
            error = "Not verified. Check your email!"
        elif check_password_hash(user[1], password):  # Assuming index 1 is password
            session["username"] = username
            session["pfp"] = user[2]  # Assuming index 2 is profile pic — update if wrong
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
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        email = request.form["email"]
        student_id = request.form["student_id"]

        if password != confirm_password:
            error = "Passwords don't match!"
            len(password) > 1000
            error = "password is too long!"
        elif (
            not email.endswith("@burnside.school.nz")
            or email.split("@")[0] != student_id
        ):
            error = "Invalid email — must be @burnside and match student ID."
        elif len(student_id) != 5 or not student_id.isdigit():
            error = "Invalid student ID"
        else:
            conn = sqlite3.connect("main.db")
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM users WHERE username = ? OR student_id = ?",
                (username, student_id),
            )
            existing_user = cursor.fetchone()

            if existing_user:
                error = "User already exists"
            elif len(username) > 10:
                error = "username too long "
            else:
                key = random.randint(1000000000, 1000000000000000000)
                hashed_password = generate_password_hash(password)
                sql = "INSERT INTO users(username, password, student_id, email, key, is_verified) VALUES(?,?,?,?,?,?)"
                cursor.execute(
                    sql, (username, hashed_password, student_id, email, key, False)
                )
                conn.commit()
                conn.close()
                send_email(email, key)
                return render_template(
                    "login.html", header="login", error="check your email."
                )

            # fix service and user_id and make sure the emailer is funtioning when signup happens.

            conn.close()

    return render_template("signup.html", header="signup", error=error)


@app.route("/verify/<int:key>")
def verify(key):
    conn = sqlite3.connect("main.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE key = ?", (key,))
    user = cursor.fetchone()
    conn.close()
    if user is not None:
        conn = sqlite3.connect("main.db")
        cursor = conn.cursor()
        sql = "UPDATE users SET is_verified = ? WHERE id = ?"
        cursor.execute(sql, (True, user[0]))
        conn.commit()
        conn.close()
    return render_template("login.html", header="login", error="you are verified")


if __name__ == "__main__":
    app.run(debug=True)
