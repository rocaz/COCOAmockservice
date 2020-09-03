#/bin/sh
# You need to run this script first.
export FLASK_APP=app.py
flask db init
flask db migrate
flask db upgrade