from flask import Flask, render_template, redirect, url_for, request
from subprocess import call

DEBUG = True

def supervisorctl(command):
   return call(['supervisorctl', command]) 

app = Flask(__name__)

@app.route('/')
def index():
    message = request.args.get('message', '')
    return render_template('index.html', message=message)

@app.route('/restart_bot/', methods=['POST'])
def restart_bot():
    if request.form['token'] == "12345":
        result = call(['supervisorctl', 'restart gdgajubot'])
        return redirect(url_for('index', message='Ok'))
    else:
        return redirect(url_for('index', message='NotOk'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=DEBUG)
