import argparse
import os
import shutil
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.schema.document import Document
from get_embading_function import get_embedding_function
from langchain.vectorstores.faiss import FAISS  # Use FAISS here instead of Chroma
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

print("Using API key:", api_key[:6] + "..." + api_key[-4:])  # for safety

FAISS_PATH = "faiss_index"  # Use this folder for FAISS persistence
DATA_PATH = "data"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Reset the database.")
    args = parser.parse_args()
    if args.reset:
        print("✨ Clearing Database")
        clear_database()

    documents = load_documents()
    chunks = split_documents(documents)
    add_to_faiss(chunks)


def load_documents():
    loader = PyPDFDirectoryLoader(DATA_PATH)
    return loader.load()


def split_documents(documents: list[Document]):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=80,
        length_function=len,
        is_separator_regex=False,
    )
    return splitter.split_documents(documents)


def add_to_faiss(chunks: list[Document]):
    embedding_fn = get_embedding_function()

    if os.path.exists(FAISS_PATH):
        db = FAISS.load_local(
            FAISS_PATH,
            embedding_fn,
            allow_dangerous_deserialization=True  # <-- Add this
        )
    else:
        db = FAISS.from_documents(chunks, embedding_fn)

    chunks_with_ids = calculate_chunk_ids(chunks)

    existing_ids = set(db.docstore._dict.keys())
    new_chunks = [c for c in chunks_with_ids if c.metadata["id"] not in existing_ids]

    if new_chunks:
        print(f"👉 Adding new documents: {len(new_chunks)}")
        db.add_documents(new_chunks)
        db.save_local(FAISS_PATH)
    else:
        print("✅ No new documents to add")


def calculate_chunk_ids(chunks):
    last_page_id = None
    current_chunk_index = 0

    for chunk in chunks:
        source = chunk.metadata.get("source")
        page = chunk.metadata.get("page")
        current_page_id = f"{source}:{page}"

        if current_page_id == last_page_id:
            current_chunk_index += 1
        else:
            current_chunk_index = 0

        chunk_id = f"{current_page_id}:{current_chunk_index}"
        last_page_id = current_page_id

        chunk.metadata["id"] = chunk_id

    return chunks


def clear_database():
    if os.path.exists(FAISS_PATH):
        shutil.rmtree(FAISS_PATH)


def query_rag(question: str) -> str:
    custom_prompt = (
        f"You are the **Strategic Business Developer** for FastAutomate, creators of the Primius.ai hybrid AI automation platform. Your specialization is in **identifying and deeply understanding a prospect’s or customer’s pain points**, then mapping them to  the right solution in the FastAutomate / Primius.ai product suite. You are a trusted advisor who adds measurable value by connecting client challenges to features, workflows, and outcomes that solve them. "
        f"Core Mission: - Diagnose the user's needs through targeted questioning. - Present accurate, KB-backed solutions from the FastAutomate ecosystem. - Position solutions in a way that drives adoption, retention, and measurable ROI. - Maintain strict product boundary rules. "
        
        f"Question: {question}"
    )
    db = FAISS.load_local(
    FAISS_PATH,
    embeddings=get_embedding_function(),
    allow_dangerous_deserialization=True
)

    retriever = db.as_retriever()

    llm = ChatOpenAI(
        model="gpt-4",
        temperature=0,
        api_key=api_key,
    )

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
    )

    result = qa_chain.invoke({"query": custom_prompt})

    return result["result"] if isinstance(result, dict) else result


if __name__ == "__main__":
    main()
