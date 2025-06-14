from inspect import ismethod
import os
from pathlib import Path
from flask import Flask, flash, redirect, render_template, request, session, url_for
import colorama
from colorama import Fore, Back, Style
from flask.cli import load_dotenv

# from flask_bcrypt import check_password_hash

colorama.init(autoreset=True)
import sqlite3

app = Flask(__name__)
dotenv_path = Path(".env")
load_dotenv(dotenv_path)
app.secret_key = os.getenv("KEY")


@app.route("/")
def home():
    header = "Home"
    return render_template("home.html", header=header)


@app.route("/test")
def test():
    header = "Test me"
    return render_template("test.html", header=header)


@app.route("/pizza")
def pizza():
    header = "pizza"
    conn = sqlite3.connect("pizza.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Pizza")
    pizzas = cursor.fetchall()
    conn.close()
    return render_template("pizzas.html", header=header, pizzas=pizzas)


@app.route("/about")
def about():
    header = "About"
    return render_template("about.html", header=header)


@app.route("/subject")
def subject_selection():
    header = "Subject Selection"
    return render_template("subject_selection.html", header=header)


@app.route("/help")
def help():
    header = "Help"
    return render_template("help.html", header=header)


@app.route("/technology")
def technology():
    header = "tech"
    return render_template("technology.html", header=header)


@app.route("/login", methods=["GET", "POST"])
def login():
    header = "login"
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = sqlite3.connect("main.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
        conn.close()
        for user in users:
            if username == user[1] and password == user[2]:
                session["username"] = username
                session["pfp"] = user[3]
                flash("You were successfully logged in")
                return redirect(url_for("home"))
        error = "invald username/password"
    return render_template("login.html", header=header, error=error)


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
            error = "passwords don't match!"
            return render_template("signup.html", header="signup", error=error)
        if (
            not email.endswith("@burnside.school.nz")
            or email.split("@")[0] != student_id
        ):
            error = "invalid email needs to be @burnside"
            return render_template("signup.html", header="signup", error=error)
        if len(student_id) != 5 or not student_id.isdigit():
            error = "invalid student id"
            return render_template("signup.html", header="signup", error=error)
        conn = sqlite3.connect("main.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
        conn.close()
        for user in users:
            if username == user[1] or student_id == user[4]:
                error = "user already exists"
                return render_template("signup.html", header="signup", error=error)
        print("kwjhehbfkwahbfkjwaeckjwBN")
        conn = sqlite3.connect("main.db")
        cursor = conn.cursor()
        sql = "INSERT INTO users(username, password, student_id, email) VALUES(?,?,?,?)"
        cursor.execute(sql, (username, password, student_id, email))
        conn.commit()
        conn.close()

        # pfp = request.form["pfp"]

        # check if email is correct check if passwords match and if student id match 5 caracters, add to the data base "new user" add signup page "signup.html"

        return redirect(url_for("login"))
    return render_template("signup.html", header="signup", error=error)


if __name__ == "__main__":
    app.run(debug=True)
