from flask import Flask, render_template
import colorama
from colorama import Fore, Back, Style 
colorama.init(autoreset=True)
import sqlite3

app = Flask(__name__)


@app.route('/')
def home():
    header = "Home"
    return render_template("home.html", header=header)


@app.route('/test')
def test():
    header = "Test me"
    return render_template("test.html", header=header)


@app.route("/pizza")
def pizza():
    header = "pizza"
    conn = sqlite3.connect("pizza.db")
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Pizza')
    pizzas = cursor.fetchall()
    conn.close()
    return render_template("pizzas.html", header=header, pizzas=pizzas)


@app.route('/about')
def about():
    header = "About"
    return render_template("about.html", header=header)


@app.route('/subject')
def subject_selection():
    header = "Subject Selection"
    return render_template("subject_selection.html", header=header)


@app.route('/help')
def help():
    header = "Help"
    return render_template("help.html", header=header)


if __name__ == '__main__':
    app.run(debug=True)