# Chat Rag

Simple chat rag bot 4.6


```bash

```
## Structure
```python
chat/
  backend/
    app.py — FastAPI: POST /upload, POST /chat, GET /documents, DELETE /documents/{id}
    rag.py — chunking, sentence-transformers + Chroma retrieval, Anthropic Sonnet 4.6 generation
    requirements.txt
    .env.example
  frontend/
    app/page.tsx — upload + chat UI
    lib/api.ts — typed API client
    package.json / tsconfig.json / next.config.js
```
## Usage

```python
# Run backend:
cd backend
python -m venv .venv; .\backend\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# edit .env -> set ANTHROPIC_API_KEY
uvicorn app:app --reload --port 8000

# Run frontend:
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
# open http://localhost:3000, backend at http://localhost:8000
```
## License

[MIT](https://choosealicense.com/licenses/mit/)