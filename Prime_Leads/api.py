import os
import json
from flask import Flask, request, jsonify
from flasgger import Swagger
from flask_cors import CORS
from dotenv import load_dotenv
from main_graph import run_graph_with_full_output

load_dotenv()

app = Flask(__name__)
CORS(app)

# Swagger UI configuration
swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "PrimeFlow Recruit",
        "description": "powered by fastautomate",
        "version": "1.0.0"
    },
    "basePath": "/"
}

swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec_1',
            "route": '/apispec_1.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/PrimeFlow/"
}

Swagger(app, config=swagger_config, template=swagger_template)

# ---------------------- API Endpoint ----------------------

@app.route("/jobDescription", methods=["POST"])
def run_pipeline():
    """
    Run Candidate Pipeline
    ---
    tags:
      - Job Description
    consumes:
      - application/json 
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            jd_text:
              type: string
              example: "We are hiring a React frontend engineer in cairo egypt"
    responses:
      200:
        description: Final candidate dispositions and full graph state
      400:
        description: Missing input
      500:
        description: Server error
    """
    data = request.get_json()

    if not data or "jd_text" not in data:
        return jsonify({"error": "Missing 'jd_text' in request body"}), 400

    try:
        result = run_graph_with_full_output({"raw_jd_text": data["jd_text"]})

        # Force dict regardless of GraphState or pure dict
        graph_state = result if isinstance(result, dict) else result.dict()

        # Safe access to scored candidates
        scored_candidates = graph_state.get("Scored_Candidate_Objects", [])

        summary = {
            "hot": len([c for c in scored_candidates if c.get("fit_score", 0) >= 8]),
            "warm": len([c for c in scored_candidates if 5 <= c.get("fit_score", 0) < 8]),
            "cold": len([c for c in scored_candidates if c.get("fit_score", 0) < 5])
        }

        return jsonify({
    "status": "success",
    "graph_state": {
        "Enriched_Candidate_Records": graph_state.get("Enriched_Candidate_Records", []),
        "Scored_Candidate_Objects": graph_state.get("Scored_Candidate_Objects", [])
    },
    "summary": summary
})


    except Exception as e:

        return jsonify({"error": str(e)}), 500



@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Welcome to PrimeFlow Recruit API – go to /PrimeFlow for Swagger UI"})

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
