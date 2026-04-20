from flask import Flask, render_template, request, redirect, url_for, session, flash, g
import boto3
import sqlite3
import uuid
import os
import re
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-in-production")

# ── S3 config ──────────────────────────────────────────────────

S3_BUCKET = "my-photo-app-bucket-123"
S3_REGION = "ap-south-1"
s3 = boto3.client('s3', region_name=S3_REGION)

# ── SQLite config — stored right on your EC2 instance ─────────
# DB file lives at /home/ec2-user/docrepo.db  (or wherever you run the app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "docrepo.db")

def get_db():
    """Return a per-request SQLite connection (stored on g)."""
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row   # rows behave like dicts
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Create tables if they don't exist yet."""
    with app.app_context():
        db = get_db()
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT    NOT NULL,
                last_name  TEXT    NOT NULL,
                email      TEXT    NOT NULL UNIQUE,
                password   TEXT    NOT NULL,
                created_at TEXT    DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS documents (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                filename    TEXT    NOT NULL,
                s3_key      TEXT    NOT NULL,
                file_size   INTEGER DEFAULT 0,
                uploaded_at TEXT    DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)
        db.commit()

init_db()

# ── Helpers ────────────────────────────────────────────────────

def validate_password(p):
    if len(p) < 8:
        return "Password must be at least 8 characters."
    if not re.search(r'\d', p):
        return "Password must contain at least one number."
    if not re.search(r'[!@#$%^&*(),.?\":{}|<>]', p):
        return "Password must contain at least one special character."
    return None

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def presigned_url(s3_key, expiry=3600):
    return s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': S3_BUCKET, 'Key': s3_key},
        ExpiresIn=expiry
    )

#  AUTH

@app.route('/')
def home():
    return redirect(url_for('dashboard') if 'user_id' in session else url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        db       = get_db()
        user     = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if user and check_password_hash(user['password'], password):
            session.update({
                'user_id':    user['id'],
                'first_name': user['first_name'],
                'last_name':  user['last_name'],
                'email':      user['email'],
            })
            return redirect(url_for('dashboard'))

        flash("Invalid email or password.", "error")
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        first = request.form.get('first_name', '').strip()
        last  = request.form.get('last_name',  '').strip()
        email = request.form.get('email',      '').strip().lower()
        pwd   = request.form.get('password',   '')
        conf  = request.form.get('confirm_password', '')

        if not all([first, last, email, pwd]):
            flash("All fields are required.", "error")
            return render_template('signup.html')
        if pwd != conf:
            flash("Passwords do not match.", "error")
            return render_template('signup.html')
        err = validate_password(pwd)
        if err:
            flash(err, "error")
            return render_template('signup.html')

        try:
            db = get_db()
            db.execute(
                "INSERT INTO users (first_name, last_name, email, password) VALUES (?,?,?,?)",
                (first, last, email, generate_password_hash(pwd))
            )
            db.commit()
        except sqlite3.IntegrityError:
            flash("An account with that email already exists.", "error")
            return render_template('signup.html')

        flash("Account created! Please sign in.", "success")
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

#  DASHBOARD

@app.route('/dashboard')
@login_required
def dashboard():
    db   = get_db()
    rows = db.execute(
        "SELECT id, filename, s3_key, file_size, uploaded_at FROM documents WHERE user_id = ? ORDER BY uploaded_at DESC",
        (session['user_id'],)
    ).fetchall()

    docs = []
    for r in rows:
        docs.append({
            'id':         r['id'],
            'filename':   r['filename'],
            's3_key':     r['s3_key'],
            'url':        presigned_url(r['s3_key']),
            'size_kb':    round(r['file_size'] / 1024, 1) if r['file_size'] else '—',
            'uploaded_at': r['uploaded_at'],
        })
    return render_template('dashboard.html', docs=docs)

#  UPLOAD

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        file = request.files.get('document')
        if not file or file.filename == '':
            flash("Please select a file.", "error")
            return render_template('upload.html')

        safe_name = os.path.basename(file.filename)
        s3_key    = f"{session['user_id']}/{uuid.uuid4()}_{safe_name}"
        file_size = len(file.read());  file.seek(0)

        try:
            s3.upload_fileobj(file, S3_BUCKET, s3_key,
                              ExtraArgs={"ContentType": file.content_type})
        except Exception as e:
            flash(f"Upload failed: {e}", "error")
            return render_template('upload.html')

        db = get_db()
        db.execute(
            "INSERT INTO documents (user_id, filename, s3_key, file_size) VALUES (?,?,?,?)",
            (session['user_id'], safe_name, s3_key, file_size)
        )
        db.commit()
        flash(f"'{safe_name}' uploaded successfully!", "success")
        return redirect(url_for('dashboard'))

    return render_template('upload.html')

#  DELETE

@app.route('/delete/<int:doc_id>', methods=['POST'])
@login_required
def delete(doc_id):
    db  = get_db()
    row = db.execute(
        "SELECT s3_key FROM documents WHERE id = ? AND user_id = ?",
        (doc_id, session['user_id'])
    ).fetchone()

    if row:
        try:
            s3.delete_object(Bucket=S3_BUCKET, Key=row['s3_key'])
        except Exception:
            pass
        db.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        db.commit()
        flash("Document deleted.", "success")
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=False)
