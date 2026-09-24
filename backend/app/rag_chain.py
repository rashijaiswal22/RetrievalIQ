import os
import json
import warnings
from typing import AsyncGenerator
import traceback
warnings.filterwarnings("ignore")

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

from langchain_core.prompts import (ChatPromptTemplate,MessagesPlaceholder)
from langchain_classic.chains.combine_documents import (create_stuff_documents_chain)
from langchain_classic.chains import (create_retrieval_chain)
from app.pdf_loader import (get_embeddings,get_bm25_retriever)
from app.config import (GEMINI_API_KEY, VECTOR_STORE_DIR)

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
    faiss_path = os.path.join(
        VECTOR_STORE_DIR,
        "faiss_index"
    )

    if not os.path.exists(faiss_path):
        return None
    try:
        vectorstore = FAISS.load_local(faiss_path, get_embeddings(), allow_dangerous_deserialization=True )

        faiss_retriever = vectorstore.as_retriever(
            search_kwargs={"k": 5 })

        bm25_retriever = get_bm25_retriever()

        if bm25_retriever:
            return EnsembleRetriever(
                retrievers=[bm25_retriever,faiss_retriever ],
                weights=[0.5,0.5])
        return faiss_retriever

    except Exception as e:
        print(f"Retriever build error: {e}")
        return None


def get_llm_with_fallbacks():
    llm_instances = []
    for model_name in AVAILABLE_MODELS:

        try:

            llm = ChatGoogleGenerativeAI(
                google_api_key=GEMINI_API_KEY,
                model=model_name,
                streaming=True,
                request_timeout=30,
                temperature=0.2,
                max_retries=1)

            llm_instances.append(llm)

        except Exception as e:

            print(f"Skipping model initialization for "f"{model_name}: {e}" )

    if not llm_instances:

        raise RuntimeError("No LLM models could be initialized.")

    primary_llm = llm_instances[0]

    if len(llm_instances) > 1:
        return primary_llm.with_fallbacks( llm_instances[1:] )

    return primary_llm


async def stream_rag_response(question: str,session_id: str) -> AsyncGenerator[str, None]:

    try:
        # 1. Build retriever
        current_retriever = build_retriever()

        if not current_retriever:
            yield ("data: "+ json.dumps( "No uploaded document is available "
                    "for answering this question." )+ "\n\n" )
            return
        
        # 2. Chat history
        history = get_session_history(session_id)

        # 3. LLM
        llm = get_llm_with_fallbacks()

        # 4. Prompt
        qa_prompt = ChatPromptTemplate.from_messages(
            [("system", "You are a document-based question "
                    "answering assistant.\n\n"

                    "SOURCE RULES:\n"
                    "1. Answer ONLY from the information "
                    "present in the retrieved document "
                    "context.\n"

                    "2. Do NOT use your own general "
                    "knowledge to add unsupported facts.\n"

                    "3. If the context does not contain "
                    "enough information, respond exactly:\n"

                    "\"The uploaded document does not contain "
                    "sufficient information to answer this "
                    "question.\"\n"

                    "4. You may combine relevant information "
                    "from multiple retrieved chunks, but "
                    "do not invent facts.\n\n"

                    "ANSWER STRUCTURE:\n"

                    "5. Start with a short direct explanation "
                    "of the answer.\n"

                    "6. Use Markdown headings for major "
                    "sections.\n"

                    "7. Use ## for main sections and ### for "
                    "subsections.\n"

                    "8. Put every heading on its own line.\n"

                    "9. Use bullet points for lists of "
                    "features, advantages, components, etc.\n"

                    "10. Use numbered lists only when "
                    "explaining sequential steps.\n"

                    "11. Use **bold** for important terms "
                    "when useful.\n"

                    "12. Do not unnecessarily repeat the "
                    "retrieved document.\n\n"

                    "CODE RULES:\n"

                    "13. If code is relevant to the question, "
                    "show the code in a Markdown fenced "
                    "code block.\n"

                    "14. The opening code fence MUST be on "
                    "its own line, like:\n"

                    "```java\n"
                    "code here\n"
                    "```\n"

                    "15. The closing code fence MUST be on "
                    "its own line.\n"

                    "16. There MUST be a newline after the "
                    "opening ```language and before the "
                    "closing ```.\n"

                    "17. NEVER put normal explanation text "
                    "on the same line as ```java, ```python, "
                    "or ```.\n"

                    "18. NEVER write a code fence followed "
                    "immediately by normal text on the same "
                    "line.\n"

                    "19. Preserve code from the retrieved "
                    "context accurately.\n"

                    "20. Do NOT invent, reconstruct, or "
                    "complete missing code.\n"

                    "21. If retrieved code is incomplete, "
                    "say that it is incomplete instead of "
                    "creating missing code.\n\n"

                    "IMPORTANT MARKDOWN RULE:\n"

                    "22. Never output malformed Markdown "
                    "such as ```the full flow: or ```code "
                    "on the same line as normal text.\n"

                    "23. Keep explanations and code blocks "
                    "separated by blank lines.\n\n"

                    "RETRIEVED DOCUMENT CONTEXT:\n"
                    "{context}"
                ),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}")
            ]
        )

        # 5. Create document QA chain
        question_answer_chain = (create_stuff_documents_chain(llm, qa_prompt) )

        # 6. Create RAG chain
        rag_chain = create_retrieval_chain(current_retriever, question_answer_chain)

        # 7. Stream response
        full_response = ""

        async for event in rag_chain.astream_events(
            {"input": question, "chat_history": history.messages}, version="v2"
        ):

            if event["event"] != "on_chat_model_stream":
                continue

            chunk = event["data"]["chunk"]

            if not chunk.content:
                continue

            text_content = chunk.content

            # It may sometimes return a list
            if isinstance(text_content, list):
                parts = []

                for item in text_content:
                    if isinstance(item, str):
                        parts.append(item)

                    elif isinstance(item, dict):
                        text = item.get("text", "")

                        if text:
                            parts.append(text)

                text_content = "".join(parts)

            # Make absolutely sure we send a string
            if not isinstance(text_content, str ):
                text_content = str(text_content)

            if not text_content:
                continue

            full_response += text_content

            # JSON encode every SSE chunk
            yield ("data: " + json.dumps(text_content) + "\n\n")

        # 8. Save conversation history
        history.add_user_message(question)
        history.add_ai_message(full_response)

    except Exception as e:
        print("=" * 70)
        print("RAG STREAMING ERROR")
        print("ERROR TYPE:", type(e).__name__)
        print("ERROR MESSAGE:", repr(str(e)))
        print("=" * 70)

        traceback.print_exc()

        if "429" in str(e) or "quota" in str(e).lower() or "rate" in str(e).lower():
            user_message = (
                 "⚠️ AI service is temporarily unavailable because "
                 "the usage limit has been reached. Please try again later."
                   )
        else:
            user_message = ( "⚠️ Something went wrong while generating the answer. "
                 "Please try again."
          )

        yield ("data: " + json.dumps(user_message) + "\n\n" )
        
    finally:
        yield ("data: [DONE]\n\n" )
    
        






