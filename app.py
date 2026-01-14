from flask import Flask, request, jsonify, session, send_from_directory
import os
from flask_cors import CORS
from models import (
    init_db, add_knowledge_item, add_validation_record,
    get_connection, create_user, verify_user, get_user_by_id
)

app = Flask(__name__)
app.secret_key = "452136589"

# CORS Configuration: Explicitly allow the frontend origin
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "http://localhost:5173"}})

# Session Configuration for Local Development
app.config.update(
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_HTTPONLY=True
)

# Ensure upload folder exists
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static/uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.before_first_request
def setup_database():
    init_db()


# Helper utilities

def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return get_user_by_id(uid)


def login_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"error": "Unauthorized"}), 401
        return fn(*args, **kwargs)
    return wrapper


# AUTHENTICATION

@app.route("/api/check-auth", methods=["GET"])
def check_auth():
    user = current_user()
    if user:
        return jsonify({"authenticated": True, "user": dict(user)})
    return jsonify({"authenticated": False}), 401


@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username").strip()
    password = data.get("password")
    role_input = data.get("role")

    if role_input == "team_leader":
        role = "team_leader"
    else:
        role = "team_member"

    try:
        uid = create_user(username, password, role)
        session["user_id"] = uid
        return jsonify({"message": "Registration successful", "user_id": uid}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username").strip()
    password = data.get("password")

    user = verify_user(username, password)
    if user:
        session["user_id"] = user["id"]
        return jsonify({"message": "Login successful", "user": dict(user)}), 200
    else:
        return jsonify({"error": "Invalid credentials"}), 401


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"}), 200


# KNOWLEDGE ITEMS

@app.route("/api/upload", methods=["POST"])
@login_required
def upload_item():
    title = request.form["title"]
    description = request.form.get("description")
    tags = request.form.get("tags")
    project_link = request.form.get("project_link")
    author_id = session.get("user_id")

    filename = None
    if "file" in request.files:
        uploaded_file = request.files["file"]
        if uploaded_file.filename != "":
            filename = uploaded_file.filename
            uploaded_file.save(os.path.join(UPLOAD_FOLDER, filename))

    add_knowledge_item(title, description, author_id, tags, project_link, filename)
    return jsonify({"message": "Upload successful"}), 201


@app.route("/api/search", methods=["GET"])
@login_required
def search():
    query = request.args.get("q", "")
    conn = get_connection()
    cur = conn.cursor()

    if query:
        cur.execute("SELECT * FROM knowledge_items WHERE title LIKE ? OR tags LIKE ?",
                    (f"%{query}%", f"%{query}%"))
    else:
        cur.execute("SELECT * FROM knowledge_items")

    rows = cur.fetchall()
    results = [dict(row) for row in rows]
    conn.close()
    
    return jsonify(results)


@app.route("/api/validate", methods=["GET", "POST"])
@login_required
def validate_items():
    user = current_user()
    
    if request.method == "POST":
        if user["role"] != "team_leader":
            return jsonify({"error": "Forbidden"}), 403

        data = request.json
        item_id = data.get("item_id")
        decision = data.get("decision")
        comments = data.get("comments")
        validator_id = user["id"]

        add_validation_record(item_id, validator_id, decision, comments)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE knowledge_items SET status = ? WHERE id = ?", (decision, item_id))
        conn.commit()
        conn.close()

        return jsonify({"message": f"Item {decision}"}), 200

    # GET pending items
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM knowledge_items WHERE status = 'submitted'")
    rows = cur.fetchall()
    pending = [dict(row) for row in rows]
    conn.close()
    return jsonify(pending)


@app.route("/api/recommendations", methods=["GET"])
@login_required
def recommendations():
    user = current_user()
    user_id = user["id"]

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT tags FROM knowledge_items WHERE author_id = ?", (user_id,))
    user_tags = [row["tags"] for row in cur.fetchall() if row["tags"]]

    all_tags = ",".join(user_tags)
    tag_keywords = [t.strip() for t in all_tags.split(",") if t.strip()]

    if tag_keywords:
        keyword = tag_keywords[0]
        cur.execute("SELECT * FROM knowledge_items WHERE tags LIKE ?", (f"%{keyword}%",))
        rows = cur.fetchall()
    else:
        cur.execute("SELECT * FROM knowledge_items LIMIT 5")
        rows = cur.fetchall()

    recs = [dict(row) for row in rows]
    conn.close()
    return jsonify(recs)


# Serve static files for downloaded content
@app.route('/static/uploads/<path:filename>')
def serve_uploads(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
