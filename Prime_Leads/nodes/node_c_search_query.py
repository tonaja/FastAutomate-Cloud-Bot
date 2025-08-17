import os
import json
from typing import Dict, List
from datetime import datetime
from pathlib import Path
from graph_state import GraphState
import google.generativeai as genai

def load_search_query_prompt() -> str | None:
    prompt_path = Path("prompts/searchQuery.txt")
    if not prompt_path.exists():
        return None
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception:
        return None

def generate_search_queries_with_gemini(icp_data: Dict, max_retries: int = 1) -> List[Dict]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not found")
    genai.configure(api_key=api_key)

    prompt_template = load_search_query_prompt()
    if not prompt_template:
        raise FileNotFoundError("Prompt file not found")
    
    prompt = prompt_template.replace("{icp_data}", json.dumps(icp_data, indent=2))
    model = genai.GenerativeModel("gemini-2.5-pro")
    generation_config = genai.GenerationConfig(
        temperature=0.1,
        max_output_tokens=16384,
        response_mime_type="application/json"
    )

    for attempt in range(max_retries + 1):
        try:
            response = model.generate_content(prompt, generation_config=generation_config)
            text = response.text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].strip()
            parsed = json.loads(text)
            if not isinstance(parsed, list):
                raise ValueError("Response is not a JSON array")
            return parsed
        except Exception as e:
            if attempt == max_retries:
                raise e

    raise RuntimeError("All attempts failed")

def search_query_generator_node(state: GraphState) -> GraphState:
    try:
        icp_data = state.ICP_GENERATOR_JSON
        if not icp_data:
            return state

        company_name = icp_data.get('company_name', 'Company')
        search_queries = generate_search_queries_with_gemini(icp_data, max_retries=2)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        queries_filename = f"outputs/{company_name}_search_queries_{timestamp}.json"
        print(f"🎯 Search Query report generated: {queries_filename}")

        os.makedirs("outputs", exist_ok=True)
        with open(queries_filename, 'w', encoding='utf-8') as f:
            json.dump(search_queries, f, indent=2, ensure_ascii=False)

        state.SEARCH_QUERY_JSON = {
            "search_queries": search_queries,
            "total_queries": len(search_queries),
            "generation_timestamp": datetime.now().isoformat(),
            "company_name": company_name,
            "model_used": "gemini-2.5-pro",
            "queries_file_path": queries_filename
        }
        return state

    except Exception:
        return state

__all__ = ['search_query_generator_node']