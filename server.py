"""
LITI Open Source - Psycholinguistic HR Analysis Tool
Flask server with SQLite persistence for self-hosted deployment
"""

import os
import json
import sqlite3
from flask import Flask, send_from_directory, send_file, request, jsonify, g

app = Flask(__name__, static_folder='.')

# Database configuration
DATABASE = os.path.join(os.path.dirname(__file__), 'data', 'liti.db')
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
DEFAULTS_FILE = os.path.join(DATA_DIR, 'prompts.json')

def get_db():
    """Get database connection for current request"""
    if 'db' not in g:
        os.makedirs(DATA_DIR, exist_ok=True)
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    """Close database connection at end of request"""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize database with tables"""
    db = get_db()
    db.executescript('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS scales (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT,
            enabled INTEGER DEFAULT 1,
            instructions TEXT
        );

        CREATE TABLE IF NOT EXISTS models (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            provider TEXT
        );

        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY,
            data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    db.commit()

    # Load defaults if database is empty
    cursor = db.execute('SELECT COUNT(*) FROM scales')
    if cursor.fetchone()[0] == 0:
        load_defaults()

def load_defaults():
    """Load default data from prompts.json"""
    try:
        with open(DEFAULTS_FILE, 'r', encoding='utf-8') as f:
            defaults = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        defaults = {"systemPrompt": "", "scales": [], "models": []}

    db = get_db()

    # Save prompts
    for key in ['systemPrompt', 'personalityPrompt', 'requirementsPrompt']:
        if key in defaults:
            db.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
                      (key, defaults[key]))

    # Save scales
    for scale in defaults.get('scales', []):
        db.execute('''INSERT OR REPLACE INTO scales (id, name, category, enabled, instructions)
                      VALUES (?, ?, ?, ?, ?)''',
                  (scale.get('id'), scale.get('name'), scale.get('category'),
                   1 if scale.get('enabled', True) else 0, scale.get('instructions', '')))

    # Save models
    for model in defaults.get('models', []):
        db.execute('INSERT OR REPLACE INTO models (id, name, provider) VALUES (?, ?, ?)',
                  (model.get('id'), model.get('name'), model.get('provider', '')))

    db.commit()

# Initialize database on startup
with app.app_context():
    init_db()

# Security headers
@app.after_request
def add_security_headers(response):
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' data: https://fonts.gstatic.com; "
        "img-src 'self' data: blob:; "
        "connect-src 'self' https://openrouter.ai https://*.openrouter.ai; "
        "worker-src 'self' blob:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )
    response.headers['Content-Security-Policy'] = csp
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response

# Static routes
@app.route('/')
def index():
    return send_file('index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    if filename.startswith('data/') or filename == 'liti.db':
        return jsonify({"error": "Access denied"}), 403
    return send_from_directory('.', filename)

# ============== SETTINGS API ==============

@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Get all settings including API key"""
    db = get_db()
    cursor = db.execute('SELECT key, value FROM settings')
    settings = {row['key']: row['value'] for row in cursor.fetchall()}
    return jsonify(settings)

@app.route('/api/settings', methods=['POST'])
def save_settings():
    """Save settings"""
    data = request.get_json()
    db = get_db()
    for key, value in data.items():
        db.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
    db.commit()
    return jsonify({"success": True})

@app.route('/api/settings/<key>', methods=['GET'])
def get_setting(key):
    """Get single setting"""
    db = get_db()
    cursor = db.execute('SELECT value FROM settings WHERE key = ?', (key,))
    row = cursor.fetchone()
    return jsonify({key: row['value'] if row else None})

@app.route('/api/settings/<key>', methods=['POST'])
def save_setting(key):
    """Save single setting"""
    data = request.get_json()
    value = data.get('value', '')
    db = get_db()
    db.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
    db.commit()
    return jsonify({"success": True})

# ============== PROMPTS API ==============

@app.route('/api/prompts', methods=['GET'])
def get_prompts():
    """Get all prompts, scales, and models"""
    db = get_db()

    # Get prompts from settings
    cursor = db.execute("SELECT key, value FROM settings WHERE key IN ('systemPrompt', 'personalityPrompt', 'requirementsPrompt')")
    prompts = {row['key']: row['value'] for row in cursor.fetchall()}

    # Get scales
    cursor = db.execute('SELECT id, name, category, enabled, instructions FROM scales ORDER BY id')
    scales = [dict(row) for row in cursor.fetchall()]
    for scale in scales:
        scale['enabled'] = bool(scale['enabled'])

    # Get models
    cursor = db.execute('SELECT id, name, provider FROM models')
    models = [dict(row) for row in cursor.fetchall()]

    return jsonify({
        "systemPrompt": prompts.get('systemPrompt', ''),
        "personalityPrompt": prompts.get('personalityPrompt', ''),
        "requirementsPrompt": prompts.get('requirementsPrompt', ''),
        "scales": scales,
        "models": models
    })

@app.route('/api/prompts', methods=['POST'])
def save_prompts():
    """Save prompts"""
    data = request.get_json()
    db = get_db()

    for key in ['systemPrompt', 'personalityPrompt', 'requirementsPrompt']:
        if key in data:
            db.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
                      (key, data[key]))
    db.commit()
    return jsonify({"success": True})

@app.route('/api/prompts/system', methods=['GET'])
def get_system_prompt():
    """Get system prompt only"""
    db = get_db()
    cursor = db.execute("SELECT value FROM settings WHERE key = 'systemPrompt'")
    row = cursor.fetchone()
    return jsonify({"systemPrompt": row['value'] if row else ''})

@app.route('/api/prompts/system', methods=['POST'])
def save_system_prompt():
    """Save system prompt"""
    data = request.get_json()
    db = get_db()
    db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('systemPrompt', ?)",
              (data.get('systemPrompt', ''),))
    db.commit()
    return jsonify({"success": True})

# ============== SCALES API ==============

@app.route('/api/prompts/scales', methods=['GET'])
def get_scales():
    """Get all scales"""
    db = get_db()
    cursor = db.execute('SELECT id, name, category, enabled, instructions FROM scales ORDER BY id')
    scales = [dict(row) for row in cursor.fetchall()]
    for scale in scales:
        scale['enabled'] = bool(scale['enabled'])
    return jsonify({"scales": scales})

@app.route('/api/prompts/scales', methods=['POST'])
def save_scales():
    """Save all scales (replace all)"""
    data = request.get_json()
    scales = data.get('scales', [])
    db = get_db()

    db.execute('DELETE FROM scales')
    for scale in scales:
        db.execute('''INSERT INTO scales (id, name, category, enabled, instructions)
                      VALUES (?, ?, ?, ?, ?)''',
                  (scale.get('id'), scale.get('name'), scale.get('category'),
                   1 if scale.get('enabled', True) else 0, scale.get('instructions', '')))
    db.commit()
    return jsonify({"success": True})

@app.route('/api/prompts/scales/<int:scale_id>', methods=['PUT'])
def update_scale(scale_id):
    """Update single scale"""
    data = request.get_json()
    db = get_db()
    db.execute('''UPDATE scales SET name=?, category=?, enabled=?, instructions=? WHERE id=?''',
              (data.get('name'), data.get('category'),
               1 if data.get('enabled', True) else 0, data.get('instructions', ''), scale_id))
    db.commit()
    return jsonify({"success": True})

@app.route('/api/prompts/scales/<int:scale_id>', methods=['DELETE'])
def delete_scale(scale_id):
    """Delete scale"""
    db = get_db()
    db.execute('DELETE FROM scales WHERE id = ?', (scale_id,))
    db.commit()
    return jsonify({"success": True})

@app.route('/api/prompts/scales/add', methods=['POST'])
def add_scale():
    """Add new scale"""
    data = request.get_json()
    db = get_db()
    cursor = db.execute('''INSERT INTO scales (name, category, enabled, instructions)
                           VALUES (?, ?, ?, ?)''',
                       (data.get('name'), data.get('category'),
                        1 if data.get('enabled', True) else 0, data.get('instructions', '')))
    db.commit()
    return jsonify({"success": True, "id": cursor.lastrowid})

# ============== MODELS API ==============

@app.route('/api/models', methods=['GET'])
def get_models():
    """Get all models"""
    db = get_db()
    cursor = db.execute('SELECT id, name, provider FROM models')
    models = [dict(row) for row in cursor.fetchall()]
    return jsonify({"models": models})

@app.route('/api/models', methods=['POST'])
def save_models():
    """Save all models (replace all)"""
    data = request.get_json()
    models = data.get('models', [])
    db = get_db()

    db.execute('DELETE FROM models')
    for model in models:
        db.execute('INSERT INTO models (id, name, provider) VALUES (?, ?, ?)',
                  (model.get('id'), model.get('name'), model.get('provider', '')))
    db.commit()
    return jsonify({"success": True})

@app.route('/api/models/add', methods=['POST'])
def add_model():
    """Add new model"""
    data = request.get_json()
    db = get_db()
    db.execute('INSERT OR REPLACE INTO models (id, name, provider) VALUES (?, ?, ?)',
              (data.get('id'), data.get('name'), data.get('provider', '')))
    db.commit()
    return jsonify({"success": True})

@app.route('/api/models/<path:model_id>', methods=['DELETE'])
def delete_model(model_id):
    """Delete model"""
    db = get_db()
    db.execute('DELETE FROM models WHERE id = ?', (model_id,))
    db.commit()
    return jsonify({"success": True})

# ============== HISTORY API ==============

@app.route('/api/history', methods=['GET'])
def get_history():
    """Get analysis history"""
    db = get_db()
    cursor = db.execute('SELECT id, data, created_at FROM history ORDER BY created_at DESC')
    history = []
    for row in cursor.fetchall():
        try:
            item = json.loads(row['data'])
            item['id'] = row['id']
            history.append(item)
        except json.JSONDecodeError:
            pass
    return jsonify({"history": history})

@app.route('/api/history', methods=['POST'])
def save_history():
    """Save entire history (replace all)"""
    data = request.get_json()
    history = data.get('history', [])
    db = get_db()

    db.execute('DELETE FROM history')
    for item in history:
        item_id = item.pop('id', None)
        db.execute('INSERT INTO history (id, data) VALUES (?, ?)',
                  (item_id, json.dumps(item, ensure_ascii=False)))
    db.commit()
    return jsonify({"success": True})

@app.route('/api/history/add', methods=['POST'])
def add_history():
    """Add new history item"""
    data = request.get_json()
    db = get_db()
    cursor = db.execute('INSERT INTO history (data) VALUES (?)',
                       (json.dumps(data, ensure_ascii=False),))
    db.commit()
    return jsonify({"success": True, "id": cursor.lastrowid})

@app.route('/api/history/<int:analysis_id>', methods=['GET'])
def get_history_item(analysis_id):
    """Get single history item"""
    db = get_db()
    cursor = db.execute('SELECT id, data FROM history WHERE id = ?', (analysis_id,))
    row = cursor.fetchone()
    if row:
        item = json.loads(row['data'])
        item['id'] = row['id']
        return jsonify(item)
    return jsonify({"error": "Not found"}), 404

@app.route('/api/history/<int:analysis_id>', methods=['DELETE'])
def delete_history_item(analysis_id):
    """Delete history item"""
    db = get_db()
    db.execute('DELETE FROM history WHERE id = ?', (analysis_id,))
    db.commit()
    return jsonify({"success": True})

# ============== RESET API ==============

@app.route('/api/reset-to-defaults', methods=['POST'])
def reset_to_defaults():
    """Reset all data to defaults"""
    db = get_db()
    db.execute('DELETE FROM settings')
    db.execute('DELETE FROM scales')
    db.execute('DELETE FROM models')
    db.execute('DELETE FROM history')
    db.commit()
    load_defaults()
    return jsonify({"success": True})

# ============== DEMO API ==============

@app.route('/api/demo-result', methods=['GET'])
def get_demo_result():
    """Get demo analysis result"""
    demo_result = {
        "id": 1733999999999,
        "date": "12.12.2025 12:12",
        "candidateName": "Demo Candidate",
        "position": "Software Engineer",
        "model": "demo",
        "isDemo": True,
        "analyzedScales": ["Сумлінність", "Екстраверсія", "Приязність", "Нейротизм", "Відкритість"],
        "scores": {
            "сумлінність": 7, "екстраверсія": 6, "приязність": 8, "нейротизм": 3, "відкритість": 7
        },
        "scaleResults": {
            "Сумлінність": {"score": 7, "rawResponse": "7"},
            "Екстраверсія": {"score": 6, "rawResponse": "6"},
            "Приязність": {"score": 8, "rawResponse": "8"},
            "Нейротизм": {"score": 3, "rawResponse": "3"},
            "Відкритість": {"score": 7, "rawResponse": "7"}
        },
        "requirementsMatch": [
            {"requirement": "Python experience", "resumeMatch": "yes", "interviewMatch": "yes", "comment": "5+ років підтверджено"},
            {"requirement": "Team leadership", "resumeMatch": "no", "interviewMatch": "unclear", "comment": "Не згадано в резюме"}
        ],
        "inputText": "Demo interview transcript...",
        "vacancyText": "Demo job description...",
        "resumeText": "Demo resume..."
    }
    return jsonify(demo_result)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
