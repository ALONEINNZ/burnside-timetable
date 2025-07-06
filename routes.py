from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask.cli import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
import colorama
import sqlite3
import os
from pathlib import Path
from flask_mail import Mail, Message
import random

from emailer import create_email, send_message

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
        print(user[7])
        if user[7] == 0:
            error = "not verified check your email!"
            return render_template("login.html", header="login", error=error)
        if user and check_password_hash(user[2], password):
            session["username"] = username
            session["pfp"] = user[3]
            flash("You successfully logged in")
            return redirect(url_for("home"))
        error = "Invalid username/password"
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
                return redirect(url_for("login"))
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
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
