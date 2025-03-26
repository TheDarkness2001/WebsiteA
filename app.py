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

# 🔥 Only Website B is allowed to access user data
ALLOWED_WEBSITES = {"http://127.0.0.1:5002"}

# 🔥 Secret API Key (Only Website B Knows This)
SECRET_API_KEY = "super_secret_key_123"

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
            file_path = os.path.normpath(file_path).replace("\\", "/").lstrip("/")
        else:
            return "Invalid file type."

        # Save user data
        users[username] = {
            "password": password,
            "image": file_path,
            "coins": 500  # ✅ Assign 500 coins to new users
        }
        save_users(users)

        session["username"] = username
        session["profile_image"] = file_path
        session["coins"] = 500  # ✅ Store coin balance in session

        return redirect(url_for("profile_page"))  # ✅ Redirect to `profile.html`

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    redirect_url = request.args.get("redirect_uri")

    if request.method == "POST":
        username = request.form["username"]
        password = sha256(request.form["password"].encode()).hexdigest()
        users = load_users()

        if username in users and users[username]["password"] == password:
            session.permanent = True  # ✅ Make session last longer
            session["username"] = username
            profile_image = users[username]["image"]
            profile_image = os.path.normpath(profile_image).replace("\\", "/").lstrip("/")
            profile_image = f"http://127.0.0.1:5001/{profile_image}"

            if redirect_url:
                return redirect(f"{redirect_url}?username={username}&profile_image={profile_image}")

            return redirect(url_for("profile"))

        return "Invalid credentials."

    return render_template("login.html", redirect_url=redirect_url)

@app.route("/profile_page")
def profile_page():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("profile.html", username=session["username"], profile_image=session["profile_image"], coins=session["coins"])


@app.route("/profile")
def profile():


    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    users = load_users()

    if username not in users:
        return "User not found."

    user_data = users[username]
    user_image = user_data["image"]
    user_coins = user_data.get("coins", 0)  # Default to 0 if no coins

    # Normalize image path for display
    user_image = os.path.normpath(user_image).replace("\\", "/").lstrip("/")
    user_image = f"http://127.0.0.1:5001/{user_image}"

    return render_template("profile.html", username=username, user_image=user_image, user_coins=user_coins)

# Logout
@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("index"))

# OAuth User Data API
@app.route("/userinfo", methods=["POST"])
def userinfo():
    api_key = request.headers.get("Authorization")  # Get API Key
    referer = request.headers.get("Referer")  # Get the website making the request
    username = request.json.get("username")  # Get username from request

    users = load_users()  # ✅ Load users from JSON

    # 🔥 1. Block requests from unknown websites
    if referer not in ALLOWED_WEBSITES:
        return jsonify({"error": "Access denied. Unauthorized website!"}), 403

    # 🔥 2. Require API Key for Authentication
    if api_key != SECRET_API_KEY:
        return jsonify({"error": "Invalid API key!"}), 403

    # 🔥 3. Only return data if the user exists
    if username in users:
        return jsonify({
           "username": username,
           "profile_image": users[username]["image"],
           "coins": users[username].get("coins", 0)  # Default to 0 if no coins
        })
    return jsonify({"error": "User not found"}), 404

@app.route("/update-coins", methods=["POST"])
def update_coins():
    api_key = request.headers.get("Authorization")  # ✅ Secure API key
    referer = request.headers.get("Referer")  # ✅ Verify source
    data = request.json

    if referer not in ALLOWED_WEBSITES or api_key != SECRET_API_KEY:
        return jsonify({"error": "Unauthorized access!"}), 403

    username = data.get("username")
    coins_change = data.get("coins_change", 0)  # Amount to add/subtract

    users = load_users()

    if username in users:
        users[username]["coins"] = max(0, users[username].get("coins", 0) + coins_change)  # Prevent negative coins
        save_users(users)
        
        # ✅ Sync session with latest coin balance
        session["coins"] = users[username]["coins"]
        
        return jsonify({"message": "Coins updated!", "new_balance": users[username]["coins"]})

    return jsonify({"error": "User not found"}), 404

# ✅ New API: Get Coins with Token Authentication
@app.route("/get-coins", methods=["GET"])
def get_coins():
    token = request.args.get("token")
    
    # Verify token
    for username, data in users.items():
        if data.get("token") == token:
            return jsonify({"coins": data["coins"]})
    
    return jsonify({"error": "Invalid token"}), 403

def update_coins_on_cubie(username, coins_change):
    headers = {
        "Authorization": SECRET_API_KEY,  # ✅ Secure API key
        "Referer": "http://127.0.0.1:5002"
    }
    response = requests.post(
        "http://127.0.0.1:5001/update-coins",
        json={"username": username, "coins_change": coins_change},
        headers=headers
    )
    return response.json()  # Return the response to handle in Website B


@app.route('/add-coin', methods=['POST'])
def add_coin():
    username = session.get('username')  # Ensure user is logged in
    if not username:
        return jsonify({"error": "User not logged in"}), 401

    with open('users.json', 'r+') as file:
        users = json.load(file)
        if username in users:
            users[username]['coins'] += 10  # ✅ Increase coins by 10
            new_balance = users[username]['coins']
            file.seek(0)
            json.dump(users, file, indent=4)
            return jsonify({"new_balance": f" Coins: {new_balance}"})

    return jsonify({"error": "User not found"}), 404

if __name__ == "__main__":
    app.run(debug=True, port=5001)
