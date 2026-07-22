from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from Chat_logic.Chat import get_answer
from Parent_agent import parent_agent
from save_as_pdf import save_as_pdf
from KG.kg import Create_KG, Store_graph_Neo4j, Store_graph_Qdrant
from langchain_neo4j import Neo4jGraph
from qdrant_client import QdrantClient
from pydantic import BaseModel
from pathlib import Path
from dotenv import load_dotenv
import logging
import asyncio
import os

load_dotenv()
logging.getLogger("neo4j.notifications").setLevel(logging.ERROR)


class RepoInput(BaseModel):
    url: str
    owner: str
    repo_name: str
    branch: str



client = QdrantClient(
    url=os.getenv('QDRANT_CLUSTER'),
    api_key=os.getenv('QDRANT_API_KEY')
)

graph = Neo4jGraph(
    url=os.getenv('NEO4J_URI'),
    username=os.getenv('NEO4J_USERNAME'),
    password=os.getenv('NEO4J_PASSWORD')
)


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

report_store: dict[str, str] = {}

@app.get("/")
async def serve_frontend():
    index_path = Path("frontend.html")
    if not index_path.exists():
        return JSONResponse(status_code=404, content={"error": "frontend.html not found"})
    return FileResponse('frontend.html')


@app.post('/analyze/{session_id}')
async def analyze(session_id: str, repo_input: RepoInput):
    """
    Stream the repository analysis. Stores the full text in memory
    so the download endpoint can generate a PDF from it.
    """
    message = (
        f'Explain this repo---> '
        f'url:{repo_input.url}, '
        f'owner:{repo_input.owner}, '
        f'repo_name:{repo_input.repo_name}, '
        f'branch:{repo_input.branch}'
    )

    async def stream_and_store():
        chunks = []
        async for chunk in parent_agent(message=message):
            chunks.append(chunk)
            yield chunk
        # store full text after streaming completes
        report_store[session_id] = ''.join(chunks)

    try:
        return StreamingResponse(stream_and_store(), media_type='text/markdown')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/download/{session_id}')
async def download_pdf(session_id: str):
    """Generate and return PDF from the stored report text."""
    text = report_store.get(session_id)
    if not text:
        raise HTTPException(
            status_code=404,
            detail='Report not found. Please analyze the repository first.'
        )
    try:
        pdf_bytes = save_as_pdf(tutorial_text=text)
        return Response(
            content=pdf_bytes,
            media_type='application/pdf',
            headers={'Content-Disposition': 'attachment; filename="repo.pdf"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



async def run_chat_loop(websocket: WebSocket, session_id: str):
    history = []
    while True:
        try:
            user_message = await websocket.receive_text()

            if user_message == "__RESTART_CHAT__":
                history = []
                await websocket.send_text("__CHAT_RESTARTED__")
                continue

            full_response = ""
            async for chunk in get_answer(message=user_message, history=history):
                full_response += chunk
                await websocket.send_text(chunk)

            history.append({"role": "user", "content": user_message})
            history.append({"role": "assistant", "content": full_response})

        except WebSocketDisconnect:
            logging.info(f"Session {session_id} disconnected")
            break
        except Exception as e:
            logging.error(f"Chat error in session {session_id}: {e}")
            try:
                await websocket.send_text(f"__CHAT_ERROR__:{str(e)}")
            except Exception:
                break

@app.websocket("/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    await websocket.accept()

    try:
        await websocket.send_text("__LOADING__")

        list_graph_docs = await Create_KG()

        try:
            client.delete_collection(collection_name="documents")
        except Exception:
            pass

        if list_graph_docs:
            await websocket.send_text("__LOG__:Clearing Neo4j graph...")
            graph.query("MATCH (n) DETACH DELETE n")

            await websocket.send_text("__LOG__:Storing graph in Neo4j...")
            Store_graph_Neo4j(list_graph_docs)

            await websocket.send_text("__LOG__:Embedding and storing in Qdrant...")
            Store_graph_Qdrant(list_graph_docs)
        else:
            await websocket.send_text("__LOG__:No documents found — skipping graph indexing")

        await websocket.send_text("__READY__")
        await run_chat_loop(websocket, session_id)

    except WebSocketDisconnect:
        logging.info(f"Session {session_id} disconnected during indexing")
    except Exception as e:
        logging.error(f"Indexing error in session {session_id}: {e}")
        try:
            await websocket.send_text(f"__ERROR__:{str(e)}")
        except Exception:
            pass
