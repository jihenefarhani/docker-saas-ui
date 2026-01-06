from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, UserMixin, current_user
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash
import docker
import os
from functools import wraps
from datetime import datetime

# --------------------------------
# App configuration
# --------------------------------
app = Flask(__name__)
app.secret_key = "dev-secret-key"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# SQLite (stored in instance/)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# --------------------------------
# Login manager
# --------------------------------
login_manager = LoginManager(app)
login_manager.login_view = "login"

# --------------------------------
# Docker client
# --------------------------------
client = docker.from_env()

# --------------------------------
# Nginx sites directory
# --------------------------------
NGINX_SITES_DIR = os.path.join(BASE_DIR, "nginx_sites")
os.makedirs(NGINX_SITES_DIR, exist_ok=True)

# --------------------------------
# Logs
# --------------------------------
LOG_DIR = os.path.join(BASE_DIR, "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "actions.log")

def log_action(user, action):
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.now()} | {user} | {action}\n")

# --------------------------------
# Database model
# --------------------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)

# --------------------------------
# User loader
# --------------------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --------------------------------
# Role-based access control
# --------------------------------
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role != "admin":
            flash("Admin access required", "error")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated

# --------------------------------
# Utils
# --------------------------------
def get_containers_data():
    containers = client.containers.list(all=True)
    data = []

    for c in containers:
        ports = c.attrs["NetworkSettings"]["Ports"]
        host_port = ""

        if ports:
            for _, bindings in ports.items():
                if bindings:
                    host_port = bindings[0]["HostPort"]
                    break

        data.append({
            "id": c.short_id,
            "name": c.name,
            "status": c.status,
            "image": c.image.tags[0] if c.image.tags else c.image.short_id,
            "port": host_port
        })

    return sorted(data, key=lambda x: x["name"])






#-----------------------------------
@app.route("/containers/<name>")
@login_required
def container_detail(name):
    try:
        c = client.containers.get(name)
        attrs = c.attrs

        ports = attrs["NetworkSettings"]["Ports"]
        port_mapping = []
        if ports:
            for k, v in ports.items():
                if v:
                    port_mapping.append(f"{k} → {v[0]['HostPort']}")

        return render_template(
            "container_detail.html",
            container={
                "name": c.name,
                "id": c.short_id,
                "image": c.image.tags[0] if c.image.tags else c.image.short_id,
                "status": c.status,
                "created": attrs["Created"],
                "command": attrs["Config"]["Cmd"],
                "ports": port_mapping,
                "mounts": attrs["Mounts"],
            }
        )
    except docker.errors.NotFound:
        flash("Container not found", "error")
        return redirect(url_for("index"))




#--------------------------------

@app.route("/containers/<name>/logs")
@login_required
def container_logs(name):
    try:
        c = client.containers.get(name)
        logs = c.logs(tail=100).decode("utf-8", errors="ignore")
        return {"logs": logs}
    except docker.errors.NotFound:
        return {"logs": "Container not found"}, 404


#-------------------------------------------

@app.route("/containers/<name>/stats")
@login_required
def container_stats(name):
    try:
        c = client.containers.get(name)
        stats = c.stats(stream=False)

        cpu_delta = (
            stats["cpu_stats"]["cpu_usage"]["total_usage"]
            - stats["precpu_stats"]["cpu_usage"]["total_usage"]
        )
        system_delta = (
            stats["cpu_stats"]["system_cpu_usage"]
            - stats["precpu_stats"]["system_cpu_usage"]
        )

        cpu_percent = 0.0
        if system_delta > 0:
            cpu_percent = (cpu_delta / system_delta) * 100

        mem_usage = stats["memory_stats"]["usage"]
        mem_limit = stats["memory_stats"]["limit"]

        return {
            "cpu": round(cpu_percent, 2),
            "mem_usage": round(mem_usage / 1024 / 1024, 2),
            "mem_limit": round(mem_limit / 1024 / 1024, 2),
        }
    except docker.errors.NotFound:
        return {}, 404


# --------------------------------
# Auth routes
# --------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()
        if user and check_password_hash(user.password, request.form["password"]):
            login_user(user)
            flash("Login successful", "success")
            return redirect(url_for("index"))
        flash("Invalid credentials", "error")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# --------------------------------
# Main routes
# --------------------------------
@app.route("/")
@login_required
def index():
    return render_template("index.html", containers=get_containers_data())

@app.route("/create", methods=["GET", "POST"])
@login_required
@admin_required
def create():
    if request.method == "GET":
        return render_template("create.html")

    name = request.form["name"]
    port = request.form["host_port"]
    image = request.form["image"]
    title = request.form.get("title", "")
    body = request.form.get("body", "")

    # Prevent duplicate container name
    if client.containers.list(all=True, filters={"name": name}):
        flash("Container name already exists", "error")
        return redirect(url_for("create"))

    # App type logic
    if image == "nginx:alpine":
        container_port = "80/tcp"
        use_volume = True
    elif image in ["data-web:latest", "devops-web:latest"]:
        container_port = "8000/tcp"
        use_volume = False
    else:
        flash("Unknown application type", "error")
        return redirect(url_for("create"))

    run_args = {
        "image": image,
        "name": name,
        "ports": {container_port: int(port)},
        "detach": True
    }

    # Nginx HTML mount
    if use_volume:
        container_dir = os.path.join(NGINX_SITES_DIR, name)
        os.makedirs(container_dir, exist_ok=True)
        index_path = os.path.join(container_dir, "index.html")

        with open(index_path, "w") as f:
            f.write(f"""<!DOCTYPE html>
<html>
<head><title>{title}</title></head>
<body>
<h1>{title}</h1>
<p>{body}</p>
<hr>
<p><b>Container:</b> {name}</p>
</body>
</html>
""")

        run_args["volumes"] = {
            index_path: {
                "bind": "/usr/share/nginx/html/index.html",
                "mode": "ro"
            }
        }

    try:
        client.containers.run(**run_args)
        log_action(current_user.username, f"Created container {name} ({image})")
        flash("Container created successfully", "success")

    except docker.errors.APIError as e:
        if "port is already allocated" in str(e):
            flash("Port already in use", "error")
        else:
            flash(f"Docker error: {e}", "error")

    return redirect(url_for("index"))

# --------------------------------
# Container actions
# --------------------------------
@app.post("/containers/<name>/start")
@login_required
@admin_required
def start_container(name):
    client.containers.get(name).start()
    log_action(current_user.username, f"Started {name}")
    return redirect(url_for("index"))

@app.post("/containers/<name>/stop")
@login_required
@admin_required
def stop_container(name):
    client.containers.get(name).stop()
    log_action(current_user.username, f"Stopped {name}")
    return redirect(url_for("index"))

@app.post("/containers/<name>/delete")
@login_required
@admin_required
def delete_container(name):
    client.containers.get(name).remove(force=True)
    log_action(current_user.username, f"Deleted {name}")
    return redirect(url_for("index"))

# --------------------------------
# Run
# --------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
