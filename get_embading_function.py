from langchain_openai import OpenAIEmbeddings
import os

def get_embedding_function():
    return OpenAIEmbeddings(api_key=os.getenv("API_KEY"))