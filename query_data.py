import argparse
import os
import shutil
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.schema.document import Document
from get_embading_function import get_embedding_function
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

print("Using API key:", api_key[:6] + "..." + api_key[-4:])  # for safety



CHROMA_PATH = "chroma"
DATA_PATH = "data"



def main():

    # Check if the database should be cleared (using the --clear flag).
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Reset the database.")
    args = parser.parse_args()
    if args.reset:
        print("✨ Clearing Database")
        clear_database()

    # Create (or update) the data store.
    documents = load_documents()
    chunks = split_documents(documents)
    add_to_chroma(chunks)


def load_documents():
    document_loader = PyPDFDirectoryLoader(DATA_PATH)
    return document_loader.load()


def split_documents(documents: list[Document]):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=80,
        length_function=len,
        is_separator_regex=False,
    )
    return text_splitter.split_documents(documents)


def add_to_chroma(chunks: list[Document]):
    # Load the existing database.
    db = Chroma(
        persist_directory=CHROMA_PATH, embedding_function=get_embedding_function()
    )

    # Calculate Page IDs.
    chunks_with_ids = calculate_chunk_ids(chunks)

    # Add or Update the documents.
    existing_items = db.get(include=[])  # IDs are always included by default
    existing_ids = set(existing_items["ids"])
    print(f"Number of existing documents in DB: {len(existing_ids)}")

    # Only add documents that don't exist in the DB.
    new_chunks = []
    for chunk in chunks_with_ids:
        if chunk.metadata["id"] not in existing_ids:
            new_chunks.append(chunk)

    if len(new_chunks):
        print(f"👉 Adding new documents: {len(new_chunks)}")
        new_chunk_ids = [chunk.metadata["id"] for chunk in new_chunks]
        db.add_documents(new_chunks, ids=new_chunk_ids)
        db.persist()
    else:
        print("✅ No new documents to add")


def calculate_chunk_ids(chunks):

    # This will create IDs like "data/monopoly.pdf:6:2"
    # Page Source : Page Number : Chunk Index

    last_page_id = None
    current_chunk_index = 0

    for chunk in chunks:
        source = chunk.metadata.get("source")
        page = chunk.metadata.get("page")
        current_page_id = f"{source}:{page}"

        # If the page ID is the same as the last one, increment the index.
        if current_page_id == last_page_id:
            current_chunk_index += 1
        else:
            current_chunk_index = 0

        # Calculate the chunk ID.
        chunk_id = f"{current_page_id}:{current_chunk_index}"
        last_page_id = current_page_id

        # Add it to the page meta-data.
        chunk.metadata["id"] = chunk_id

    return chunks


def clear_database():
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)


def query_rag(question: str) -> str:
    custom_prompt = (
        f"You are the **Strategic Business Developer** for FastAutomate, creators of the Primius.ai hybrid AI automation platform. Your specialization is in **identifying and deeply understanding a prospect’s or customer’s pain points**, then mapping them to  the right solution in the FastAutomate / Primius.ai product suite. You are a trusted advisor who adds measurable value by connecting client challenges to features, workflows, and outcomes that solve them. "
        f"Core Mission: - Diagnose the user's needs through targeted questioning. - Present accurate, KB-backed solutions from the FastAutomate ecosystem. - Position solutions in a way that drives adoption, retention, and measurable ROI. - Maintain strict product boundary rules. "
        f"""
## Product Boundaries

- **PrimeLeads** → Lead identification, enrichment, scoring, ranking, shortlisting. **No outreach.**  
- **PrimeRecruits** → Candidate identification, profiling, scoring, shortlisting. **No outreach.**  
- **PrimeReachOut** → Exclusive owner of outreach, messaging, reply analysis/scoring, and calendar scheduling.  
- **PrimeVision** → Intelligent RPA for document/data workflows.  
- **PrimeCRM** → CRM hygiene, enrichment, and automation.  

Any user request involving sending messages, emailing, contacting, following up, or scheduling **must be routed to PrimeReachOut**.  

## Tone & Style

- Professional, concise, and confident.  
- Positive framing, solution-oriented, and helpful.  
- Warm and approachable without being casual.  
- Avoid jargon unless requested; explain in simple, relevant terms.  
- Never speak negatively about competitors.  

## Conversational Flow

1. **Greet & Identify Context**: Welcome the user, confirm their role/business context.  
2. **Assess Needs**: Ask 2–3 strategic, open-ended questions to clarify their pain points.  
3. **Map to Solutions**: Use KB facts to recommend the right product(s) while respecting boundaries.  
4. **Explain Value**: Present benefits, relevant features, and potential outcomes.  
5. **Guide Next Steps**: Offer actionable paths—demo, workflow run, documentation, PrimeReachOut handoff.  
6. **Escalate if Needed**: KB gap → ask clarifying questions → human support if still unclear.  

## Proactive Behaviors

- Suggest related KB articles or additional product modules if relevant.  
- Anticipate adjacent needs based on the user's industry, role, or workflow.  
- Always confirm before triggering PrimeReachOut actions.  

## Examples

- **User:** "Find and email 100 high-value leads."  
  **Agent:** "PrimeLeads can identify and score the high-value leads. Then PrimeReachOut can take over for personalized outreach and scheduling."  

- **User:** "Can you set up interviews with these candidates?"  
  **Agent:** "PrimeRecruits can shortlist the candidates for you. For contacting and scheduling interviews, we’ll pass them to PrimeReachOut."  

## Guardrails

- Stay within FastAutomate/Primius.ai domain knowledge.  
- Avoid unsupported claims or speculation.  
- Never attribute outreach functions to PrimeLeads or PrimeRecruits.  
- Always ground answers in KB content before responding.  

"""
 f"Question: {question}"
    )
    db = Chroma(
    persist_directory="chroma", 
    embedding_function=get_embedding_function()
)
    retriever = db.as_retriever()

    llm = ChatOpenAI(
    model="gpt-4",  
    temperature=0,
    api_key=api_key  )


    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever
    )

    result = qa_chain.invoke({"query": custom_prompt})

    return result["result"] if isinstance(result, dict) else result

if __name__ == "__main__":
    main()