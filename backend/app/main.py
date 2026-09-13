from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List
import shutil
import os

from app.config import UPLOAD_DIR
from app.pdf_loader import process_pdfs_and_create_retrievers
from app.rag_chain import stream_rag_response, get_session_history

app = FastAPI(title='Advanced Multi-PDF Hybrid RAG API')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

class QueryModel(BaseModel):
    question: str
    session_id: str = "default_session"

@app.post('/upload')
async def upload_pdfs(files: List[UploadFile] = File(...)):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    saved_paths = []

    for file in files:
        if not file.filename.lower().endswith(('.pdf','.docx','.pptx','.ppt','.txt')):
            raise HTTPException(status_code=400, detail=f'File {file.filename} is not supported')
        
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, 'wb') as buffer:
            shutil.copyfileobj(file.file, buffer)
        saved_paths.append(file_path)

    try:
        chunks, doc_count = process_pdfs_and_create_retrievers(saved_paths)
        return {"message": f"Successfully processed {doc_count} the file", "chunks": chunks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/chat/stream')
async def chat_stream(query: QueryModel):
    return StreamingResponse(
        stream_rag_response(query.question, query.session_id), media_type='text/event-stream',
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disables proxy buffering
        }
    )

@app.get('/history/{session_id}')
async def get_history(session_id: str):
    history = get_session_history(session_id)
    messages= []
    for msg in history.messages:
        messages.append({
            'sender': 'user' if msg.type == 'human' else 'bot', 'text': msg.content
        })
    return {'session_id': session_id, 'messages': messages}





    