import os
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
UPLOAD_DIR = 'uploaded_docs'
VECTOR_STORE_DIR = 'vector_db'

HF_TOKEN = os.getenv('HF_TOKEN')
if HF_TOKEN:
    os.environ['HF_TOKEN'] = HF_TOKEN

os.makedirs(UPLOAD_DIR,exist_ok=True)
os.makedirs(VECTOR_STORE_DIR,exist_ok=True)




