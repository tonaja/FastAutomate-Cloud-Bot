from flask import Flask, request, jsonify
from main_graph import graph  
app = Flask(__name__)

@app.route('/run', methods=['POST'])
def run_graph():
    data = request.json
    jd_text = data.get("raw_jd_text", "").strip()
    
    if not jd_text:
        return jsonify({"error": "Job description is required."}), 400
    
    try:
        final_state = graph.invoke({"raw_jd_text": jd_text})
        return jsonify({"Final_Dispositions": final_state.get("Final_Dispositions", [])})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
