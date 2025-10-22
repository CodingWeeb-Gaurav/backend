import os
import json
import aiohttp
from typing import List, Dict, Any, Optional, Union, Callable
from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from langchain_core.tools import BaseTool
from langchain_core.messages import AIMessage, HumanMessage
from core.config import settings

class HTTPRequestTool(BaseTool):
    """General HTTP Request Tool for all API calls"""
    name: str = "http_request"
    description: str = """Make HTTP requests to external APIs. Use this for:
    - Searching products
    - Fetching user addresses  
    - Getting industry lists
    - Placing orders
    - Any other API calls
    
    The tool accepts full HTTP request details including URL, method, headers, and body."""
    
    def __init__(self):
        super().__init__()
        self.base_headers = {
            "Content-Type": "application/json",
            "x-user-type": "Buyer",
            "x-auth-language": "English"
        }
    
    async def _arun(self, 
                   url: str, 
                   method: str = "GET", 
                   headers: Dict = None, 
                   body: Dict = None, 
                   query_params: Dict = None) -> str:
        """Make HTTP request with full customization"""
        try:
            # Merge base headers with request-specific headers
            request_headers = {**self.base_headers, **(headers or {})}
            
            print(f"🌐 HTTP Request: {method} {url}")
            print(f"📦 Headers: {request_headers}")
            if body:
                print(f"📝 Body: {body}")
            
            async with aiohttp.ClientSession() as session:
                if method.upper() == "GET":
                    async with session.get(
                        url, 
                        headers=request_headers, 
                        params=query_params, 
                        ssl=False
                    ) as response:
                        return await self._handle_response(response)
                        
                elif method.upper() == "POST":
                    async with session.post(
                        url, 
                        headers=request_headers, 
                        json=body, 
                        ssl=False
                    ) as response:
                        return await self._handle_response(response)
                        
                elif method.upper() == "PATCH":
                    async with session.patch(
                        url, 
                        headers=request_headers, 
                        json=body, 
                        ssl=False
                    ) as response:
                        return await self._handle_response(response)
                        
                elif method.upper() == "PUT":
                    async with session.put(
                        url, 
                        headers=request_headers, 
                        json=body, 
                        ssl=False
                    ) as response:
                        return await self._handle_response(response)
                        
                elif method.upper() == "DELETE":
                    async with session.delete(
                        url, 
                        headers=request_headers, 
                        ssl=False
                    ) as response:
                        return await self._handle_response(response)
                        
                else:
                    return f"❌ Unsupported HTTP method: {method}"
                    
        except Exception as e:
            error_msg = f"❌ HTTP request failed: {str(e)}"
            print(error_msg)
            return error_msg
    
    async def _handle_response(self, response) -> str:
        """Handle HTTP response"""
        print(f"📡 Response Status: {response.status}")
        
        try:
            response_text = await response.text()
            if response.status in [200, 201]:
                # Try to parse as JSON, fallback to text
                try:
                    data = json.loads(response_text)
                    print(f"✅ API Success - Response: {json.dumps(data, indent=2)[:500]}...")
                    return json.dumps(data, indent=2)
                except json.JSONDecodeError:
                    print(f"✅ API Success - Response: {response_text[:500]}...")
                    return response_text
            else:
                error_msg = f"❌ HTTP Error {response.status}: {response_text}"
                print(error_msg)
                return error_msg
        except Exception as e:
            error_msg = f"❌ Response handling failed: {str(e)}"
            print(error_msg)
            return error_msg
    
    def _run(self, *args, **kwargs):
        """Sync version - not used but required by BaseTool"""
        raise NotImplementedError("Only async supported")

class MemoryTool(BaseTool):
    """Tool for reading/writing session memory"""
    name: str = "session_memory"
    description: str = """Read and write data to session memory for persistence across conversations.
    Use this to store user selections, product choices, request types, and other important data."""
    
    def __init__(self, session_storage):
        super().__init__()
        self.session_storage = session_storage
    
    async def _arun(self, operation: str, session_id: str, data: Dict = None) -> str:
        """Handle memory operations"""
        try:
            if operation == "read":
                session_state = await self.session_storage.get_session(session_id)
                return json.dumps(session_state, default=str)
                
            elif operation == "write" and data:
                await self.session_storage.update_session_state(session_id, data)
                return "✅ Memory updated successfully"
                
            elif operation == "update_request":
                new_state = data.get("request") if data else "select_product"
                await self.session_storage.update_session_state(session_id, {
                    "request": new_state
                })
                return f"✅ Request state updated to: {new_state}"
                
            else:
                return "❌ Invalid memory operation. Use: read, write, or update_request"
                
        except Exception as e:
            error_msg = f"❌ Memory operation failed: {str(e)}"
            print(error_msg)
            return error_msg
    
    def _run(self, *args, **kwargs):
        raise NotImplementedError("Only async supported")

class N8NAgent:
    def __init__(
        self,
        tools: List[BaseTool],
        memory: Optional[ConversationBufferMemory] = None,
        system_prompt: Optional[str] = None,
        mode: str = "output"
    ):
        """
        n8n-style AI Agent with OpenRouter support
        """
        self.tools = tools
        self.memory = memory or ConversationBufferMemory(return_messages=True, memory_key="chat_history")
        self.mode = mode
        
        # Configure LLM with OpenRouter
        llm_config = {
            "model": "anthropic/claude-3-sonnet",  # OpenRouter model
            "temperature": 0.1,
            "api_key": settings.OPENROUTER_API_KEY,
            "base_url": settings.OPENROUTER_BASE_URL,
            "default_headers": {
                "HTTP-Referer": "http://localhost:3000",
                "X-Title": "Falcon Chatbot"
            }
        }
        
        self.llm = ChatOpenAI(**llm_config)

        # n8n-style prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt or "You are a helpful AI assistant."),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        # Create agent executor
        self.agent = create_tool_calling_agent(llm=self.llm, tools=tools, prompt=self.prompt)
        self.executor = AgentExecutor(
            agent=self.agent, 
            tools=tools, 
            memory=self.memory, 
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=3
        )

    async def run(self, prompt: str, **kwargs) -> Union[str, Dict[str, Any]]:
        """
        Run the agent with the given prompt
        """
        try:
            print(f"🤖 Agent executing with prompt: {prompt[:200]}...")
            result = await self.executor.ainvoke({"input": prompt}, **kwargs)
            
            if self.mode == "input":
                return result
            else:  # output mode
                output = result.get("output", "No output generated.")
                print(f"🤖 Agent output: {output[:200]}...")
                return output
                
        except Exception as e:
            error_msg = f"❌ Agent execution error: {e}"
            print(error_msg)
            return error_msg