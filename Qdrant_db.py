from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
from qdrant_client.models import PointStruct
from dotenv import load_dotenv
import uuid
import os
load_dotenv()
from openai import OpenAI

client_openai = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

client = QdrantClient(
    url=os.getenv('QDRANT_CLUSTER'),
    api_key=os.getenv('QDRANT_API_KEY')
)

def store_in_Qdrant(chunks:list, collection_name="documents"): 
    points=[]
    
    collection_name = "documents"

    if not client.collection_exists(collection_name):  
        client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=1536,
            distance=Distance.COSINE
        )
    )    

    #to avoid multiple collections get created
    for i, chunk in enumerate(chunks):
        response = client_openai.embeddings.create(
            model="text-embedding-3-small",
            input=chunk['text'])
        
        payload=chunk
        id=str(uuid.uuid4())
        points.append(
            PointStruct(
                id=id,
                vector=response.data[0].embedding,
                payload=payload
            )
        )
    client.upsert(
    collection_name=collection_name,
    points=points)
            