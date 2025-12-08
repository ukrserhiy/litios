"""
LITI - Psycholinguistic HR Analysis Tool
Flask server with API for prompts and history management
"""

import os
import json
from flask import Flask, send_from_directory, send_file, request, jsonify

app = Flask(__name__, static_folder='.')

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
PROMPTS_FILE = os.path.join(DATA_DIR, 'prompts.json')
HISTORY_FILE = os.path.join(DATA_DIR, 'history.json')

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

def load_json(filepath, default):
    """Load JSON file or return default if not exists"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default

def save_json(filepath, data):
    """Save data to JSON file"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Static routes
@app.route('/')
def index():
    return send_file('index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

# API: Prompts
@app.route('/api/prompts', methods=['GET'])
def get_prompts():
    """Get all prompts (system prompt and scales)"""
    data = load_json(PROMPTS_FILE, {"systemPrompt": "", "scales": []})
    return jsonify(data)

@app.route('/api/prompts', methods=['POST'])
def save_prompts():
    """Save all prompts"""
    data = request.get_json()
    save_json(PROMPTS_FILE, data)
    return jsonify({"success": True})

@app.route('/api/prompts/system', methods=['GET'])
def get_system_prompt():
    """Get system prompt only"""
    data = load_json(PROMPTS_FILE, {"systemPrompt": "", "scales": []})
    return jsonify({"systemPrompt": data.get("systemPrompt", "")})

@app.route('/api/prompts/system', methods=['POST'])
def save_system_prompt():
    """Save system prompt only"""
    data = load_json(PROMPTS_FILE, {"systemPrompt": "", "scales": []})
    new_prompt = request.get_json().get("systemPrompt", "")
    data["systemPrompt"] = new_prompt
    save_json(PROMPTS_FILE, data)
    return jsonify({"success": True})

@app.route('/api/prompts/scales', methods=['GET'])
def get_scales():
    """Get scales only"""
    data = load_json(PROMPTS_FILE, {"systemPrompt": "", "scales": []})
    return jsonify({"scales": data.get("scales", [])})

@app.route('/api/prompts/scales', methods=['POST'])
def save_scales():
    """Save scales only"""
    data = load_json(PROMPTS_FILE, {"systemPrompt": "", "scales": []})
    new_scales = request.get_json().get("scales", [])
    data["scales"] = new_scales
    save_json(PROMPTS_FILE, data)
    return jsonify({"success": True})

@app.route('/api/prompts/scales/<int:scale_id>', methods=['PUT'])
def update_scale(scale_id):
    """Update a single scale"""
    data = load_json(PROMPTS_FILE, {"systemPrompt": "", "scales": [], "models": []})
    scale_data = request.get_json()

    for i, scale in enumerate(data.get("scales", [])):
        if scale.get("id") == scale_id:
            data["scales"][i] = {**scale, **scale_data}
            save_json(PROMPTS_FILE, data)
            return jsonify({"success": True})

    return jsonify({"error": "Scale not found"}), 404

# API: Models
@app.route('/api/models', methods=['GET'])
def get_models():
    """Get all AI models"""
    data = load_json(PROMPTS_FILE, {"systemPrompt": "", "scales": [], "models": []})
    return jsonify({"models": data.get("models", [])})

@app.route('/api/models', methods=['POST'])
def save_models():
    """Save all models"""
    data = load_json(PROMPTS_FILE, {"systemPrompt": "", "scales": [], "models": []})
    new_models = request.get_json().get("models", [])
    data["models"] = new_models
    save_json(PROMPTS_FILE, data)
    return jsonify({"success": True})

@app.route('/api/models/add', methods=['POST'])
def add_model():
    """Add a new model"""
    data = load_json(PROMPTS_FILE, {"systemPrompt": "", "scales": [], "models": []})
    new_model = request.get_json()
    data["models"].append(new_model)
    save_json(PROMPTS_FILE, data)
    return jsonify({"success": True})

@app.route('/api/models/<path:model_id>', methods=['DELETE'])
def delete_model(model_id):
    """Delete a model by ID"""
    data = load_json(PROMPTS_FILE, {"systemPrompt": "", "scales": [], "models": []})
    data["models"] = [m for m in data.get("models", []) if m.get("id") != model_id]
    save_json(PROMPTS_FILE, data)
    return jsonify({"success": True})

# API: History
@app.route('/api/history', methods=['GET'])
def get_history():
    """Get all analysis history"""
    data = load_json(HISTORY_FILE, [])
    return jsonify(data)

@app.route('/api/history', methods=['POST'])
def save_history():
    """Save entire history (replace)"""
    data = request.get_json()
    save_json(HISTORY_FILE, data)
    return jsonify({"success": True})

@app.route('/api/history/add', methods=['POST'])
def add_to_history():
    """Add new analysis to history"""
    history = load_json(HISTORY_FILE, [])
    new_entry = request.get_json()
    history.insert(0, new_entry)  # Add to beginning
    save_json(HISTORY_FILE, history)
    return jsonify({"success": True, "id": new_entry.get("id")})

@app.route('/api/history/<int:analysis_id>', methods=['GET'])
def get_analysis(analysis_id):
    """Get single analysis by ID"""
    history = load_json(HISTORY_FILE, [])
    for entry in history:
        if entry.get("id") == analysis_id:
            return jsonify(entry)
    return jsonify({"error": "Analysis not found"}), 404

@app.route('/api/history/<int:analysis_id>', methods=['DELETE'])
def delete_analysis(analysis_id):
    """Delete analysis by ID"""
    history = load_json(HISTORY_FILE, [])
    history = [e for e in history if e.get("id") != analysis_id]
    save_json(HISTORY_FILE, history)
    return jsonify({"success": True})

@app.route('/api/test-openrouter', methods=['POST'])
def test_openrouter():
    """Test OpenRouter API call from server side"""
    import urllib.request
    import urllib.error

    data = request.get_json()
    api_key = data.get('apiKey')
    model = data.get('model', 'anthropic/claude-haiku-4.5')

    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": "Return only a number from 0 to 10"},
            {"role": "user", "content": "Rate this: Hello world"}
        ],
        "max_tokens": 10,
        "temperature": 0.1
    }).encode('utf-8')

    req = urllib.request.Request(
        'https://openrouter.ai/api/v1/chat/completions',
        data=payload,
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            return jsonify({"success": True, "result": result})
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        return jsonify({"success": False, "error": str(e), "body": error_body}), e.code
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
