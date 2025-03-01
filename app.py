from flask import Flask, render_template, request, jsonify
import requests
import time
import google.generativeai as genai

app = Flask(__name__)

# Configure Google Gemini API
GEMINI_API_KEY = "AIzaSyDYr50bothHOxbmyMyiPTC4LVmvqhjmqkw"  # Replace with your actual Gemini API key
genai.configure(api_key=GEMINI_API_KEY)

# Judge0 API Configuration
JUDGE0_API_URL = "https://judge0-ce.p.rapidapi.com"
RAPIDAPI_KEY = "8c5b255e43msh7f6345c94783713p11ea52jsn3fc347cffa18A"  # Replace with your Judge0 API Key
HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": "judge0-ce.p.rapidapi.com",
    "Content-Type": "application/json"
}

# Language IDs for Judge0 API
LANGUAGE_IDS = {
    "Python": 71,
    "C": 50,
    "C++": 54,
    "Java": 62
}

@app.route('/')
def index():
    topics = ["Array", "Linked List", "Graph", "Tree", "Dynamic Programming"]
    return render_template('index.html', topics=topics)

@app.route('/get_question', methods=['POST'])
def get_question():
    topic = request.json['topic']
    prompt = f"Generate a challenging problem statement for {topic} in Data Structures & Algorithms with sample input-output format."
    
    try:
        model = genai.GenerativeModel("gemini-1.5-pro-latest")
        response = model.generate_content(prompt)
        question = response.text.strip()
    except Exception as e:
        return jsonify({"error": f"Error fetching question: {str(e)}"})
    
    return jsonify({"question": question})

@app.route('/run_code', methods=['POST'])
def run_code():
    data = request.json
    source_code = data.get("code", "")
    language = data.get("language", "Python")  # Default to Python
    stdin = data.get("stdin", "")

    language_id = LANGUAGE_IDS.get(language)
    if not language_id:
        return jsonify({"error": "Unsupported language"}), 400

    payload = {
        "source_code": source_code,
        "language_id": language_id,
        "stdin": stdin
    }
    
    # Submit code to Judge0
    response = requests.post(f"{JUDGE0_API_URL}/submissions", json=payload, headers=HEADERS)
    if response.status_code != 201:
        return jsonify({"error": "Failed to create submission"}), response.status_code

    # Get the token to track execution
    token = response.json().get("token")
    if not token:
        return jsonify({"error": "No token received"}), 500

    # Poll Judge0 API for result
    while True:
        result_response = requests.get(f"{JUDGE0_API_URL}/submissions/{token}", headers=HEADERS)
        if result_response.status_code != 200:
            return jsonify({"error": "Failed to fetch submission result"}), result_response.status_code
        
        result = result_response.json()
        if result.get("status", {}).get("id") not in [1, 2]:  # Not in queue or processing
            break
        time.sleep(1)  # Wait before polling again

    return jsonify({
        "stdout": result.get("stdout", ""),
        "stderr": result.get("stderr", ""),
        "compile_output": result.get("compile_output", ""),
        "message": result.get("message", ""),
        "status": result.get("status", {}).get("description", "")
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)