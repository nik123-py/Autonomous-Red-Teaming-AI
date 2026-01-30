"""
Simple vulnerable API for ART-AI simulation.
Contains intentional vulnerabilities for educational purposes.
DO NOT USE IN PRODUCTION.
"""

from flask import Flask, request, jsonify
import sqlite3
import os

app = Flask(__name__)

# In-memory database for demo
DB_PATH = "/tmp/vulnerable_api.db"

def init_db():
    """Initialize database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            password TEXT,
            role TEXT DEFAULT 'user'
        )
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO users (username, password, role)
        VALUES ('admin', 'admin123', 'admin'),
               ('user', 'password', 'user')
    """)
    conn.commit()
    conn.close()

@app.route('/')
def index():
    """Health check"""
    return jsonify({
        "status": "online",
        "service": "Vulnerable API",
        "warning": "This is a vulnerable application for educational purposes only"
    })

@app.route('/api/users', methods=['GET'])
def get_users():
    """Get users - vulnerable to SQL injection"""
    user_id = request.args.get('id', '')
    
    # VULNERABLE: Direct string interpolation
    query = f"SELECT id, username, role FROM users WHERE id = {user_id}"
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        conn.close()
        
        users = [{"id": r[0], "username": r[1], "role": r[2]} for r in results]
        return jsonify(users)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """Login endpoint - vulnerable to authentication bypass"""
    data = request.get_json() or {}
    username = data.get('username', '')
    password = data.get('password', '')
    
    # VULNERABLE: Weak authentication
    if username == 'admin' and password == 'admin123':
        return jsonify({
            "success": True,
            "token": "fake_token_12345",
            "role": "admin"
        })
    elif username == 'user' and password == 'password':
        return jsonify({
            "success": True,
            "token": "fake_token_67890",
            "role": "user"
        })
    else:
        return jsonify({"success": False, "error": "Invalid credentials"}), 401

@app.route('/api/search', methods=['GET'])
def search():
    """Search endpoint - vulnerable to XSS"""
    query = request.args.get('q', '')
    
    # VULNERABLE: No output encoding
    return jsonify({
        "query": query,
        "results": [f"Result for: {query}"]
    })

@app.route('/api/file', methods=['GET'])
def get_file():
    """File endpoint - vulnerable to path traversal"""
    filename = request.args.get('name', '')
    
    # VULNERABLE: No path validation
    try:
        file_path = f"/tmp/{filename}"
        with open(file_path, 'r') as f:
            content = f.read()
        return jsonify({"content": content})
    except Exception as e:
        return jsonify({"error": str(e)}), 404

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)

