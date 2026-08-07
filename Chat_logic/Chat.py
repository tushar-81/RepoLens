from agents import Agent, Runner, trace, function_tool
from KG.Graph_RAG import Graph_Query_Qdrant, traversal_query
from openai.types.responses import ResponseTextDeltaEvent

from openai import OpenAI
from Chat_logic.prompt import CHAT_AGENT_INSTRUCTION 
from dotenv import load_dotenv
import os
import logging
load_dotenv()

@function_tool
def Query_VectorDB(message:str):
    '''
    When to call:
    If the history isn't sufficient to answer user's question, use the tool to query VectorDB (Qdrant) and retrieve relevant docs.

    What to pass:
    message : user's question

    What does the function return:
    It returns the retrived information as a string to make it LLM ingestible.  

    What to do next:
    Return the retrieved information to Chat_Agent to give user the response
    '''
    results=Graph_Query_Qdrant(message)
    final_string=traversal_query(results, message)
    return final_string

tools=[Query_VectorDB]

client=OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

Chat_agent=Agent(name='Chat_Agent', instructions=CHAT_AGENT_INSTRUCTION , tools=tools, model='gpt-4o-mini')

async def get_answer(message:str, history:list, collection='documents'):
    with trace(workflow_name="Github Repo", group_id=collection):
        result= Runner.run_streamed(starting_agent=Chat_agent, input=(history + [{"role": "user", "content": message}]), context=history)
        async for event in result.stream_events():
            if event.type=='raw_response_event' and isinstance(event.data, ResponseTextDeltaEvent):
                yield event.data.delta

