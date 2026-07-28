def build_prompt(question: str, doc_context: str, graph_context: str, traversal_text: str):
    
    prompt = f"""
Each source provides different information:
- Code Chunks: raw source code, useful for implementation details
- Graph Descriptions: entities and relationships extracted from code, useful for understanding structure
- Graph Traversal: how entities connect to each other, useful for understanding flow and dependencies

-------------------------------
CODE CHUNKS
-------------------------------
{doc_context}

-------------------------------
GRAPH DESCRIPTIONS
-------------------------------
{graph_context}

-------------------------------
GRAPH TRAVERSAL
-------------------------------
{traversal_text}

-------------------------------
USER'S QUESTION
-------------------------------
{question}

-------------------------------
INSTRUCTIONS
-------------------------------
- Synthesize information across all three sources
- If sources contradict each other, prefer the Code Chunks as ground truth
- If the answer is not in the context, say so clearly
- Reference specific file names and function names where relevant
"""
    return prompt
