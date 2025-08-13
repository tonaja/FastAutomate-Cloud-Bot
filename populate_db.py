import argparse
import hashlib
import os
import shutil
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.schema.document import Document
from get_embading_function import get_embedding_function
from langchain.vectorstores.faiss import FAISS  # <- use FAISS instead of Chroma

CHROMA_PATH = "faiss_index"  # change directory name if you want
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

    if os.path.exists(CHROMA_PATH):
        # Load existing FAISS index and metadata
        db = FAISS.load_local(
    CHROMA_PATH,
    embedding_fn,
    allow_dangerous_deserialization=True
)

    else:
        # Create new FAISS index
        db = FAISS.from_documents(chunks, embedding_fn)

    # Calculate IDs and assign to chunks metadata
    chunks_with_ids = calculate_chunk_ids(chunks)

    ids = [c.metadata["id"] for c in chunks_with_ids]
    print("Unique IDs generated:", len(set(ids)), "out of", len(ids))


    # Filter out already existing document IDs
    existing_ids = set(db.docstore._dict.keys())
    new_chunks = [c for c in chunks_with_ids if c.metadata["id"] not in existing_ids]

    if new_chunks:
        print(f"👉 Adding new documents: {len(new_chunks)}")
        db.add_documents(new_chunks)
        db.save_local(CHROMA_PATH)
    else:
        print("✅ No new documents to add")



def calculate_chunk_ids(chunks):
    for chunk in chunks:
        # Use md5 hash of the chunk text to ensure uniqueness
        content_hash = hashlib.md5(chunk.page_content.encode('utf-8')).hexdigest()
        
        source = chunk.metadata.get("source", "unknown_source")
        page = chunk.metadata.get("page", "unknown_page")
        
        chunk.metadata["id"] = f"{source}:{page}:{content_hash}"
    
    return chunks


def clear_database():
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)


if __name__ == "__main__":
    main()
