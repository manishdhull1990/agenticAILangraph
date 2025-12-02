from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.tools import tool
from dotenv import load_dotenv
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

#1. LLM
llm = ChatOpenAI()

#2. Tools
client = MultiServerMCPClient({
    "math": {
        "transport": "stdio",
        "command": "C:\\Python313\\Scripts\\uv.exe",
        "args": ["run", "fastmcp", "run", "D:/mcp_math_server/main.py"]
    },
    "expense": {
        "transport": "streamable_http",
        "url": "https://soft-black-jellyfish.fastmcp.app/mcp"
    }
})


# 3. State
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

async def build_graph():

    tools = await client.get_tools()
    print(tools)

    llm_with_tools = llm.bind_tools(tools)

    # 4. Nodes
    async def chat_node(state: ChatState):
        """LLM node that may answer or request a tool call."""
        messages = state['messages']
        response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

    tool_node = ToolNode(tools)
    # 6. Graph
    graph = StateGraph(ChatState)
    graph.add_node("chat_node", chat_node)
    graph.add_node("tools", tool_node)

    graph.add_edge(START, "chat_node")
    graph.add_conditional_edges("chat_node",tools_condition)
    graph.add_edge('tools', 'chat_node')

    chatbot = graph.compile()
    return chatbot

async def main():
    chatbot = await build_graph()
    #running the graph
    result = await chatbot.ainvoke({'messages':[HumanMessage(content='Summarize expense starting from  2020 till 2025')]})
    print("AI:", result['messages'][-1].content)

if __name__== '__main__':
    asyncio.run(main())