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

# Function to check allowed file types
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Function to load users
def load_users():
    try:
        with open(USER_DATA_FILE, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# Function to save users
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
        password = sha256(request.form["password"].encode()).hexdigest()
        file = request.files["image"]

        users = load_users()

        if username in users:
            return "Username already exists. Choose a different one."

        # Save image if valid
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(file_path)
            file_path = os.path.normpath(file_path).replace("\\", "/").lstrip("/")  # Normalize and fix path
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
# Login page in Website A
@app.route("/login", methods=["GET", "POST"])
def login():
    redirect_url = request.args.get("redirect_uri")  # Get the redirect_uri from Website B

    if request.method == "POST":
        username = request.form["username"]
        password = sha256(request.form["password"].encode()).hexdigest()

        users = load_users()

        if username in users and users[username]["password"] == password:
            session["username"] = username
            profile_image = users[username]["image"]
            profile_image = os.path.normpath(profile_image).replace("\\", "/").lstrip("/")
            profile_image = f"http://127.0.0.1:5001/{profile_image}"

            if redirect_url:
                # 🔥 Redirect back to Website B with full user info
                return redirect(f"{redirect_url}?username={username}&password={password}&profile_image={profile_image}")

            return redirect(url_for("profile"))

        return "Invalid credentials."

    return render_template("login.html", redirect_url=redirect_url)

    redirect_url = request.args.get("redirect")

    if request.method == "POST":
        username = request.form["username"]
        password = sha256(request.form["password"].encode()).hexdigest()

        users = load_users()

        if username in users and users[username]["password"] == password:
            session["username"] = username
            profile_image = users[username]["image"]
            profile_image = os.path.normpath(profile_image).replace("\\", "/").lstrip("/")
            profile_image = f"http://127.0.0.1:5001/{profile_image}"

            if redirect_url:
                return redirect(f"{redirect_url}?username={username}&profile_image={profile_image}")

            return redirect(url_for("profile"))

        return "Invalid credentials."

    return render_template("login.html", redirect_url=redirect_url)

# Profile page
@app.route("/profile")
def profile():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    users = load_users()
    user_image = users[username]["image"]
    user_image = os.path.normpath(user_image).replace("\\", "/").lstrip("/")
    user_image = f"http://127.0.0.1:5001/{user_image}"

    return f"Welcome, {username}! <br><img src='{user_image}' width='150'>"

# Logout
@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("index"))

# OAuth Authorization (API endpoint for Website B)
@app.route("/authorize", methods=["POST"])
def authorize():
    username = request.json.get("username")
    password = sha256(request.json.get("password").encode()).hexdigest()

    users = load_users()
    if username in users and users[username]["password"] == password:
        profile_image = users[username]["image"]
        profile_image = os.path.normpath(profile_image).replace("\\", "/").lstrip("/")
        profile_image = f"http://127.0.0.1:5001/{profile_image}"
        
        return jsonify({
            "access_token": "VALID_TOKEN",
            "username": username,
            "portfolio_image": profile_image
        })
    return jsonify({"error": "Invalid credentials"}), 401

# Login with redirect (for OAuth flow)
@app.route('/login_with_redirect')
def login_with_redirect():
    redirect_url = request.args.get('redirect')
    if not redirect_url:
        return "Invalid request", 400
    
    if "username" not in session:
        return redirect(url_for("login", redirect=redirect_url))

    username = session["username"]
    users = load_users()
    profile_image = users[username]["image"]
    profile_image = os.path.normpath(profile_image).replace("\\", "/").lstrip("/")
    profile_image = f"http://127.0.0.1:5001/{profile_image}"

    return redirect(f"{redirect_url}?username={username}&profile_image={profile_image}")

if __name__ == "__main__":
    app.run(debug=True, port=5001)