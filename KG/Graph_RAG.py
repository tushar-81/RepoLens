from openai import OpenAI
from langchain_neo4j import Neo4jGraph
from dotenv import load_dotenv
from qdrant_client.models import Filter, FieldCondition, MatchValue
from qdrant_client import QdrantClient
from qdrant_client.models import PayloadSchemaType
from KG.create_prompt import build_prompt
import os
load_dotenv()
Open_Ai=os.getenv('OPENAI_API_KEY')
client_openai = OpenAI(api_key=Open_Ai)

client = QdrantClient(
    url=os.getenv('QDRANT_CLUSTER'),
    api_key=os.getenv('QDRANT_API_KEY')
)

graph=Neo4jGraph(
    url=os.getenv('NEO4J_URI'),
    username=os.getenv('NEO4J_USERNAME'),
    password=os.getenv('NEO4J_PASSWORD'),
    
)

def Graph_Query_Qdrant(message:str):
    message_embedding=client_openai.embeddings.create(
            model="text-embedding-3-small",
            input=message)
    
    #for selective search for qdrant created a payload_index
    client.create_payload_index(
        collection_name="documents",
        field_name="Source_type",
        field_schema=PayloadSchemaType.KEYWORD)

    results = client.query_points(
        collection_name="documents",
        query=message_embedding.data[0].embedding,
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="Source_type",
                    match=MatchValue(value="Graph_Document")
                )
            ]
        ),
        limit=3
    )
    return results

def traversal_query(results, message:str):
    traversal_results=[]
    code_results=[]
    graph_data=[]

    for result in results.points:
        graph_file=result.payload['file']
        graph_name=result.payload['name']
        graph_data.append(str(f'file name : {graph_file}'))
        graph_data.append(str(f'name : {graph_name}'))

        code_text=result.payload['Code']
        code_results.append(code_text)
        node_ids=result.payload['Nodes']
        
        for node_ID in node_ids:
            node_id=node_ID.get('node_id')

        #traversal query to get 
            result_query = graph.query("""
            MATCH (n {id: $node_id})-[r*1..2]-(neighbor)
            RETURN n.id AS source,
                   type(r[-1]) AS relationship,
                   neighbor.id AS target,
                   labels(neighbor) AS target_labels
            """, params={"node_id": node_id})
        
            traversal_results.extend(result_query)
    
    traversal_lines = [
        f"{row['source']} --[{row['relationship']}]--> {row['target']}"
        for row in traversal_results
    ]
    graph_traversal = "\n".join(traversal_lines)    

    graph_description=',\n'.join(graph_data)

    code_string=', \n'.join(code_results)
    
    final_prompt=build_prompt(question=message, 
                              doc_context=code_string, 
                              graph_context=graph_description, 
                              traversal_text=graph_traversal)
    
    return final_prompt
