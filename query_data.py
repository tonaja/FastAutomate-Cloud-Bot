import argparse
import os
import shutil
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.schema.document import Document
from get_embading_function import get_embedding_function
from langchain.vectorstores.faiss import FAISS  
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import sys
sys.path.append(os.path.abspath("C:\\Users\\FaceGraph\\Downloads\\FastAutomate_PrimeLeads\\new-folder\\Prime_Leads"))
from main_graph import main_PrimeLeads


load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")



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


## New Special Rule for PrimeLeads
- If the user asks to **use PrimeLeads**, do NOT try to answer directly.
- Instead, reply: "🔗 Please provide the URL you want PrimeLeads to process."
- Wait for the user to provide the URL.
- After the URL is provided, the system will call the function `main_primeleads(url)` to execute.
- Keep your reply short and clear when asking for the URL.
"""
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

    answer = result["result"] if isinstance(result, dict) else result

    # --- NEW LOGIC: check if PrimeLeads is requested ---
    if "prime leads" in question.lower():
        return "🔗 Please provide the URL you want PrimeLeads to process."

    return answer


if __name__ == "__main__":
    main()
