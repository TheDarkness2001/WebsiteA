from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json
import os
from werkzeug.utils import secure_filename
from hashlib import sha256

app = Flask(__name__)
app.secret_key = "your_secret_key"

# File path for storing user data
USER_DATA_FILE = "users.json"

# Folder to store uploaded images
UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Allowed image extensions
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Default users (optional)
default_users = {
    "user1": {
        "password": sha256("password123".encode()).hexdigest(),
        "image": "static/uploads/default1.png"
    },
    "user2": {
        "password": sha256("mypassword".encode()).hexdigest(),
        "image": "static/uploads/default2.png"
    },
    "user3": {
        "password": sha256("test123".encode()).hexdigest(),
        "image": "static/uploads/default3.png"
    }
}

# Ensure users.json exists and is valid
if not os.path.exists(USER_DATA_FILE):
    with open(USER_DATA_FILE, "w") as file:
        json.dump(default_users, file, indent=4)
else:
    try:
        with open(USER_DATA_FILE, "r") as file:
            data = json.load(file)
            if not isinstance(data, dict):  # If file is corrupted, reset it
                raise ValueError
    except (json.JSONDecodeError, ValueError):
        with open(USER_DATA_FILE, "w") as file:
            json.dump(default_users, file, indent=4)

# Function to check allowed file types
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Function to load users from JSON
def load_users():
    try:
        with open(USER_DATA_FILE, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# Function to save users to JSON
def save_users(users):
    with open(USER_DATA_FILE, "w") as file:
        json.dump(users, file, indent=4)

# Home page
@app.route("/")
def index():
    return render_template("index.html")

# Registration page
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = sha256(request.form["password"].encode()).hexdigest()  # Hash the password
        file = request.files["image"]

        users = load_users()

        if username in users:
            return "Username already exists. Choose a different one."

        # Save image if valid
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(file_path)
        else:
            return "Invalid file type."

        # Save user data
        users[username] = {
            "password": password,
            "image": file_path
        }
        save_users(users)

        return redirect(url_for("login"))

    return render_template("register.html")

# Login page
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = sha256(request.form["password"].encode()).hexdigest()

        users = load_users()

        if username in users and users[username]["password"] == password:
            session["username"] = username
            return redirect(url_for("profile"))

        return "Invalid credentials."

    return render_template("login.html")

# Profile page
@app.route("/profile")
def profile():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    users = load_users()
    user_image = users[username]["image"]

    return f"Welcome, {username}! <br><img src='/{user_image}' width='150'>"

# Logout
@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
