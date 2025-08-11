import streamlit as st
from query_data import query_rag  # your custom RAG pipeline
from dotenv import load_dotenv
import os

load_dotenv()

st.set_page_config(page_title="RAG Chatbot", layout="centered")
st.title("Ask Fast Automate ChatBot")

st.markdown("""
This assistant uses **your uploaded knowledge base** + **LLM reasoning**  
to generate answers based only on your data.  
""")

# Question input
question = st.text_area("🔎 Ask a question:", height=100)

# Handle submission
if st.button("Get Answer"):
    if not question.strip():
        st.warning("Please enter a valid question.")
    else:
        with st.spinner("Querying your knowledge base + LLM..."):
            try:
                answer = query_rag(question)
                st.success("✅ Answer Generated")
                st.markdown("### 🤖 LLM Answer (RAG-based)")
                st.write(answer)

            except Exception as e:
                st.error(f"❌ Error during RAG query:\n{e}")
