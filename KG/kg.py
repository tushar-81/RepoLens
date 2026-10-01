from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_neo4j import Neo4jGraph
from langchain_openai import ChatOpenAI
from qdrant_client.models import VectorParams, Distance
from langchain_core.documents import Document
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
import uuid
import os
import asyncio
load_dotenv()
from KG.graph_docs_Qdrant import create_string_payload
import logging

from openai import OpenAI

client_openai = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

client = QdrantClient(
    url=os.getenv('QDRANT_CLUSTER'),
    api_key=os.getenv('QDRANT_API_KEY')
)

graph=Neo4jGraph(
    url=os.getenv('NEO4J_URI'),
    username=os.getenv('NEO4J_USERNAME'),
    password=os.getenv('NEO4J_PASSWORD'),

)
sempaphore=asyncio.Semaphore(3)

import os
load_dotenv()
OPENAI_KEY=os.getenv('OPENAI_API_KEY')
   
   
llm=ChatOpenAI(model='gpt-4o-mini', api_key=OPENAI_KEY, temperature=0)

llm_transformer=LLMGraphTransformer(llm=llm)

async def Create_KG(collection_name:str='documents'):
    points=[]
    offset=None
    i=0

    while True:
        i+=1
        result, offset= client.scroll(
            collection_name=collection_name,
            limit=50,
            with_payload=True,
            with_vectors=False,
            offset=offset
        )
        logging.info(f'point loaded {i}')
        points.extend(result)

        if offset is None:
            break
    
    document=[]
    for point in points:
        payload = point.payload

        text = payload.get('text')
        if not text:  # ✅ skip points with no text
            logging.warning(f"Skipping point {point.id} — no text field in payload")
            continue

        doc = Document(
        page_content=text,
        metadata={
            'file':       payload.get('file', 'unknown'),
            'node_type':  payload.get('node_type', 'unknown'),
            'name':       payload.get('name', 'unknown'),
            'start_line': payload.get('start_line', 0),
            'end_line':   payload.get('end_line', 0),
            'Source_type': 'Graph_Document',
        }
    )
        document.append(doc)

    sempaphore=asyncio.Semaphore(3)
    graph_documents=[]
    async def semaphore_doc_processing(doc):
        async with sempaphore:
            logging.info(f'Creating Graph Doc')
            return await llm_transformer.aconvert_to_graph_documents([doc])
        
    tasks=[semaphore_doc_processing(doc) for doc in document]
    graph_documents=await asyncio.gather(*tasks)
    list_graph_docs=[graph[0] for graph in graph_documents]
    return list_graph_docs


def Store_graph_Neo4j(documents):
    graph.add_graph_documents(
        documents,
        baseEntityLabel=True,
        include_source=True
    )

def Store_graph_Qdrant(graph_docs, collection_name='documents'):
    list_graph_docs=create_string_payload(graph_docs)
    points=[]
    try:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=1536,
                distance=Distance.COSINE
            )
        )
    except Exception:
        pass
    
    for graph_doc in list_graph_docs:
        text=graph_doc.get('TEXT')
        response = client_openai.embeddings.create(
            model="text-embedding-3-small",
            input=text)

        payload=graph_doc.get('PAYLOAD')
        id=uuid.uuid4()
        points.append(
            PointStruct(
                id=str(id),
                vector=response.data[0].embedding,
                payload=payload
            )
        )
    client.upsert(
    collection_name=collection_name,
    points=points)
    logging.info('Graph Docs stored in Qdrant')