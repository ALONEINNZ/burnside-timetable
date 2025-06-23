from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask.cli import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
import colorama
import sqlite3
import os
from pathlib import Path

from emailer import create_email, send_message

colorama.init(autoreset=True)

# Load environment variables
dotenv_path = Path(".env")
load_dotenv(dotenv_path)

app = Flask(__name__)
app.secret_key = os.getenv("KEY")


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
                hashed_password = generate_password_hash(password)
                sql = "INSERT INTO users(username, password, student_id, email) VALUES(?,?,?,?)"
                cursor.execute(sql, (username, hashed_password, student_id, email))
                conn.commit()
                conn.close()
                message = create_email(
                    "burnsidetimetable@gmail.com",
                    email,
                    "please verify your email",
                    "hello",
                )
                send_message(service, user_id, message)
                return redirect(url_for("login"))

            conn.close()

    return render_template("signup.html", header="signup", error=error)


@app.route("/verify/<int:key>")
def verify(key):
    pass


if __name__ == "__main__":
    app.run(debug=True)
