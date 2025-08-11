from query_data import query_rag
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

print("Using API key:", api_key[:6] + "..." + api_key[-4:])  # for safety




EVAL_PROMPT = """
Expected Response: {expected_response}
Actual Response: {actual_response}
---
(Answer with 'true' or 'false') Does the actual response match the expected response? 
"""


def test_monopoly_rules():
    assert query_and_validate(
        question="please give me the shortest answer u can give, and answer this questipon: We're not officially married, is that okay?",
        expected_response="Unfortunately, for us to confirm the booking, the couple must be married — this is due to local regulations and building rules.",
    )


def test_ticket_to_ride_rules():
    assert query_and_validate(
        question="We have a عرفي (customary) marriage",
        expected_response="Then it’s acceptable, But you have to send us a photo of the document",
    )


def query_and_validate(question: str, expected_response: str):
    response_text = query_rag(question)
    prompt = EVAL_PROMPT.format(
        expected_response=expected_response, actual_response=response_text
    )

    model = ChatOpenAI(
    model="gpt-4",  # or "gpt-3.5-turbo"
    temperature=0,
    api_key=api_key  # from os.getenv("OPENAI_API_KEY")
)
    evaluation_results_str = model.invoke(prompt)
    evaluation_results_str_cleaned = evaluation_results_str.content.strip().lower()


    print(prompt)

    if "true" in evaluation_results_str_cleaned:

        print("\033[92m" + f"Response: {evaluation_results_str_cleaned}" + "\033[0m")
        return True
    
    elif "false" in evaluation_results_str_cleaned:
        print("\033[91m" + f"Response: {evaluation_results_str_cleaned}" + "\033[0m")
        return False
    else:
        raise ValueError(
            f"Invalid evaluation result. Cannot determine if 'true' or 'false'."
        )