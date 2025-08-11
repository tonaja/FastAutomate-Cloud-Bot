from dotenv import load_dotenv
import os

# 🔄 Load the .env file so Python can read from it
load_dotenv()

# 🗝️ Get your API key from environment variables
api_key = os.getenv("OPENAI_API_KEY")

# 🔁 You can now use the API key in your code
print("Using API key:", api_key[:6] + "..." + api_key[-4:])  # for safety
