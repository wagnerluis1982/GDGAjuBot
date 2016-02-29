from flask import Flask, render_template, redirect, url_for, request
from subprocess import call

DEBUG = True

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/restart_bot/', methods=['POST'])
def restart_bot():
    if request.form['token'] == "1234":
        call(['supervisorctl', 'reload gdgajubot'])
        redirect(url_for('/'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=DEBUG)