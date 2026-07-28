## Creating a list containing the text and payload
def create_string_payload(graph_docs:list):

    lists=[]
    
    for graph_doc in graph_docs:
        payload={}
        temp_string=''
        source=graph_doc.source

        for key,value in source.metadata.items():
            payload[key]=value
            temp_string+=f'{key.upper()} : {value}\n'

        temp_string+=f'CODE : {source.page_content}\n'
        payload['Code']=source.page_content

        nodes=graph_doc.nodes
        nodes_list=[]
        for node in nodes:
            nodes_list.append({'node_id':node.id, 'type':node.type})
         
        temp_string+=f'NODES : {nodes_list}'
        payload['Nodes']=nodes_list

        relationships_list=[]
        relationships=graph_doc.relationships
        for relationship in relationships:
            relationships_list.append(f'{relationship.source.id} {relationship.type} {relationship.target.id}')

        
        temp_string+=f'NODES_RELATIONSHIP : {relationships_list}'   
        payload["Node_Relationship"]=relationships_list
        payload['Source_type']='Graph_Document'
        payload['String_GraphDoc']=temp_string
        
        lists.append({'TEXT': temp_string, 'PAYLOAD' : payload})
    
    return lists