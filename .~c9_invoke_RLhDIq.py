import sqlite3

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

from helpers import login_required

# Configure application
application = Flask(__name__)

# Ensure templates are auto-reloaded
application.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)
application.config["SESSION_FILE_DIR"] = mkdtemp()
application.config["SESSION_PERMANENT"] = False
application.config["SESSION_TYPE"] = "filesystem"
Session(application)

# connecting to the database  
connection = sqlite3.connect("dojo.db", check_same_thread=False) 
db = connection.cursor() 

# Get user_id
user_id = session.get("user_id")

# Ensure responses aren't cached
@application.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@application.route("/")
def index():
    if user_id:
        rows = db.execute("SELECT * FROM plans WHERE user_id = :user_id", {"user_id": user_id).fetchall()
        return render_template("index.html", rows=rows)
    
    return render_template("index.html")
    
@application.route("/logout")
def logout():
    
    session.clear()
    return redirect("/")
    
@application.route("/modules")
def modules():
    return render_template("modules.html")

@application.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "GET":
        return render_template("create.html")
    else:
        
        # Check if name
        name = request.form.get("name")
        if not name:
            return render_template("create.html", error = "Please enter a plan name.")
            
        description = request.form.get("description")
        private = request.form.get("private")
        if private == "Public":
            private = 0
        else:
            private = 1
            
        create_date = datetime.now()
        
        db.execute("INSERT INTO plans (user_id, name, description, private, create_date) VALUES (:user_id, :name, :description, :private, :create_date)", {"user_id": session["user_id"], "name": name, "description": description, "private": private, "create_date": create_date})
        connection.commit()
        
        plan_id = db.execute("SELECT plan_id FROM plans WHERE user_id = :user_id AND create_date = :create_date", {"user_id": session["user_id"], "create_date": create_date}).fetchone()[0]
        if not plan_id:
            return render_template("create.html", error = "Problem fetching plan id.")
        else:
            return render_template(url_for('edit', plan_id=plan_id))
        
    return render_template("create.html", error="Something went wrong")

@application.route('/<int:plan_id>/edit', methods=('GET', 'POST'))
@login_required
def edit(plan_id):
    plan = get_plan(plan_id)

    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db.execute(
                'UPDATE post SET title = ?, body = ?'
                ' WHERE id = ?',
                (title, body, id)
            )
            db.commit()
            return redirect("/")
    
    print(plan)
    return render_template('edit.html', plan=plan)
    

@application.route("/login", methods=["GET", "POST"])
def login():
    
    # Forget any user id
    session.clear()
    
    if request.method == "GET":
        return render_template("login.html")
    else:
        
        # Ensure email was submitted
        email = request.form.get("email")
        if not email:
            return render_template("login.html", error = "Must enter an email")
        
        # Ensure password was submitted
        password = request.form.get("password")
        if not password:
            return render_template("login.html", error = "Must enter password.")
        
        # Query database for username
        db.execute("SELECT * FROM users WHERE email=:email", {"email": email})
        rows = db.fetchall()
        
        # Check username and password are correct
        if len(rows) != 1 or not check_password_hash(rows[0][3], password):
            return render_template("login.html", error = "Invalid username and/or password")
        
        # Remember which user has logged in
        session["user_id"] = rows[0][0]
        
        # Redirect to homepage
        return redirect("/")

@application.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    else:
        
        # Check name
        name = request.form.get("name")
        if not name:
            return render_template("register.html", error = "Must enter a name.")
        
        # Check email
        email = request.form.get("email")
        if not email:
            return render_template("register.html", error = "Must enter an email.")
        
        # Check if email already exists
        db.execute("SELECT * FROM users WHERE email=:email", {"email": email})
        rows = db.fetchall()
        if len(rows) != 0:
            return render_template("register.html", error = "Email already exists.")
        
        # Check password
        password = request.form.get("password")
        if not password:
            return render_template("register.html", error = "Must enter a password.")
        confirmation = request.form.get("confirmation")
        if not confirmation:
            return render_template("register.html", error = "Must confirm your password.")
        elif password != confirmation:
            return render_template("register.html", error = "Passwords do not match.")
        
        # Hash password
        hash = generate_password_hash(password)
        
        # Creat user
        db.execute("INSERT INTO users (name, email, hash) VALUES (:name, :email, :hash)", {"name": name, "email": email, "hash": hash})
        connection.commit()
        
        # Remember which user has logged in
        # -- Get user id
        db.execute("SELECT user_id FROM users WHERE email=:email", {"email": email})
        rows = db.fetchall()
        print(rows)
        session["user_id"] = rows[0][0]
        
        return redirect("/")
        
    return render_template("register.html")
    
def get_plan(plan_id, check_user=True):
    plan = db.execute(
        'SELECT name, description, user_id'
        ' FROM plans'
        ' WHERE plan_id = ?',
        (plan_id,)
    ).fetchone()

    if plan is None:
        error = "Plan id doesn't exist"
        return render_template("index.html", error=error)

    if check_user and plan['user_id'] != session["user_id"]:
        error = "This plan is owned by another user."
        return render_template("index.html", error=error)

    return plan



# Close sqlite connection
# connection.close()