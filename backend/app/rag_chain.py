import os
import warnings
from typing import AsyncGenerator

warnings.filterwarnings('ignore')

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain_community.chat_message_histories import ChatMessageHistory

try:
    from langchain_classic.retrievers import EnsembleRetriever
except ImportError:
    try:
        from langchain.retrievers import EnsembleRetriever
    except ImportError:
        from langchain_community.retrievers import EnsembleRetriever

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains import create_retrieval_chain

from app.pdf_loader import embeddings, get_bm25_retriever
from app.config import GEMINI_API_KEY, VECTOR_STORE_DIR

store = {}

AVAILABLE_MODELS = [
    "gemini-3.6-flash",
    "gemini-2.5-flash",
    "gemini-1.5-flash"
]

def get_session_history(session_id: str):
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

def build_retriever():
    faiss_path = os.path.join(VECTOR_STORE_DIR, 'faiss_index')
    if not os.path.exists(faiss_path):
        return None

    try:
        vectorstore = FAISS.load_local(faiss_path, embeddings, allow_dangerous_deserialization=True)
        faiss_retriever = vectorstore.as_retriever(search_kwargs={'k': 5})

        bm25_retriever = get_bm25_retriever()
        if bm25_retriever:
            return EnsembleRetriever(retrievers=[bm25_retriever, faiss_retriever], weights=[0.5, 0.5])
        return faiss_retriever
    except Exception as e:
        print(f'Retriever build error: {e}') 
        return None

def get_llm_with_fallbacks():
    llm_instances = []
    for model_name in AVAILABLE_MODELS:
        try:
            llm = ChatGoogleGenerativeAI(
                google_api_key=GEMINI_API_KEY,
                model=model_name,
                streaming=True,
                request_timeout=15,
                temperature=0.2,
                max_retries=1
            )
            llm_instances.append(llm)
        except Exception as e:
            print(f"Skipping model initialization for {model_name}: {e}")

    if not llm_instances:
        raise RuntimeError("No LLM models could be initialized.")

    primary_llm = llm_instances[0]
    if len(llm_instances) > 1:
        return primary_llm.with_fallbacks(llm_instances[1:])
    return primary_llm


async def stream_rag_response(question: str, session_id: str) -> AsyncGenerator[str, None]:
    try:
        current_retriever = build_retriever()
        history = get_session_history(session_id)
        llm = get_llm_with_fallbacks()

        # Strict Prompt to prevent LaTeX and force exact PDF matching
        # Fixed Prompt - Escape all raw curly braces with {{}}
        qa_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful AI assistant.\n"
        "STRICT GUIDELINES:\n"
        "1. Use ONLY the provided Context to answer the question. Do not use outside knowledge.\n"
        "2. If the answer is in the context, extract and summarize directly from the context.\n"
        "3. DO NOT use LaTeX equations, $$, or complex syntax unless specifically asked for math.\n"
        "4. Output clean, readable Markdown text.\n\n"
        "Context:\n{context}"),
        MessagesPlaceholder('chat_history'),
        ('human', '{input}'),
        ])

        
        question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)

        if current_retriever:
            rag_chain = create_retrieval_chain(current_retriever, question_answer_chain)
        else:
            rag_chain = question_answer_chain

        full_response = ""

        async for event in rag_chain.astream_events(
            {
                'input': question,
                'chat_history': history.messages
            },
            version='v2'
        ):
            if event['event'] == 'on_chat_model_stream':
                chunk = event['data']['chunk']
                if chunk.content:
                    text_content = chunk.content
                    if isinstance(text_content, list):
                        text_content = "".join([item.get('text', '') for item in text_content if isinstance(item, dict)])

                    if text_content:
                        full_response += text_content
                        # Standard SSE chunk formatting without escaping newlines incorrectly
                        yield f"data: {text_content}\n\n"

        history.add_user_message(question)
        history.add_ai_message(full_response)

    except Exception as e:
        yield f"data: Error: {str(e)}\n\n"   

    finally:
        yield "data: [DONE]\n\n"

