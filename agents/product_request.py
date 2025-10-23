# agents/product_request.py
import asyncio
import json
import ssl
from openai import AsyncOpenAI
import aiohttp
import certifi

# Initialize Async client for OpenRouter
client = AsyncOpenAI(
    api_key="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",
    base_url="https://openrouter.ai/api/v1"
)

async def fetch_inventory_query(query: str):
    """
    Fetch products from inventory API - Tool for AI to call
    """
    print(f"🔍 AI calling inventory API: {query}")
    url = "https://nischem.com:2053/inventory/getQueryResult"
    headers = {
        "Content-Type": "application/json",
        "x-user-type": "Buyer", 
        "x-auth-language": "English"
    }
    data = {"query": query}
    
    try:
        # Create SSL context to handle certificate issues
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.patch(url, headers=headers, json=data, ssl=False) as response:
                result = await response.json()
                print(f"✅ API call successful, found {len(result.get('results', {}).get('products', []))} products")
                return result
    except Exception as e:
        print(f"❌ API call failed: {e}")
        return {"error": True, "results": {"products": []}}

async def update_session_memory(updates: dict):
    """
    Update session memory - Tool for AI to call
    """
    print(f"💾 AI updating session memory: {updates}")
    return {"status": "success", "updates": updates}

async def handle_product_request(user_input: str, session_data: dict):
    """
    Agent 1: Product Request Handler - n8n AI Agent pattern
    """
    try:
        # Initialize session data
        session_data.setdefault("history", [])
        
        print(f"🤖 Agent 1 - Current agent: '{session_data.get('agent')}'")
        print(f"📝 User input: '{user_input}'")
        
        # Check if we should hand over (agent field determines routing)
        if session_data.get("agent") != "product_request":
            print("🚫 Handover condition - agent 1 idle")
            return "I'll hand you over to the next specialist.", session_data
        
        # Process with AI using tool calling
        ai_response = await process_with_ai_tools(user_input, session_data)
        
        # Update session from AI's tool calls
        if "session_updates" in ai_response:
            for key, value in ai_response["session_updates"].items():
                if value:
                    session_data[key] = value
                    print(f"💾 Updated session: {key} = {value}")
        
        # Add to history
        session_data["history"].append({
            "user": user_input,
            "agent": ai_response["response"]
        })
        
        return ai_response["response"], session_data
        
    except Exception as e:
        print(f"❌ Error in handle_product_request: {e}")
        error_msg = "I apologize, but I'm having trouble processing your request. Please try again."
        return error_msg, session_data

async def process_with_ai_tools(user_input: str, session_data: dict):
    """
    Core AI processing with tool calling - Fixed for OpenRouter compatibility
    """
    # Build comprehensive system prompt
    system_prompt = """You are a **specialized Order Assistant** for internal lab use.
You are the **FIRST agent** in a multi-agent workflow. Your job ends when you successfully collect:
1. A confirmed product selection
2. A confirmed request type (sample, quotation, ppr, or order)

CRITICAL RULES - YOU MUST FOLLOW THESE:
1. **Memory Check**: On EVERY message, first check if agent is "product_request". If not, DO NOT respond - just return idle.
2. **Product Search**: When user mentions ANY product, IMMEDIATELY call fetch_inventory_query
3. **No Product Invention**: NEVER invent or show products that don't exist in API response
4. **Empty Results**: If API returns 0 products, inform user and suggest alternatives
5. **Confirmation Required**: ALWAYS get explicit confirmation before finalizing selections
6. **Valid Request Types**: Only accept "sample", "quotation", "ppr", or "order" - nothing else

CONVERSATION FLOW:
1. **Greeting**: Welcome user and ask what they need
2. **Product Search**: Use fetch_inventory_query when products mentioned
3. **Product Presentation**: Show available products in clear numbered list with: name_en, brand_en
4. **Product Selection**: Help user choose one product by number, name, or brand
5. **Product Confirmation**: Show full product details and get explicit confirmation
6. **Request Type**: Ask for request type if not already specified
7. **Final Confirmation**: Confirm both product AND request type before handover

SESSION UPDATE RULES (use update_session_memory tool):
- Update ONLY when user explicitly confirms both product AND request type
- Set product_id: Use exact _id from selected product
- Set product_name: Use exact name_en from selected product  
- Set product_details: Store FULL product object
- Set request: "sample", "quotation", "ppr", or "order" ONLY
- Set agent: "request_details" ONLY when handing over

GUARDRAILS:
- Never hand over without explicit user confirmation
- Never update session for partial information
- Never accept invalid request types
- Never proceed without verifying product availability

CURRENT SESSION STATE:
- agent: product_request (you are active)
- request: (empty until user selects)
- product_id: (empty until user selects)
- product_name: (empty until user selects)"""

    # Prepare messages
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    # Add conversation history
    history = session_data.get("history", [])
    for entry in history[-6:]:
        messages.append({"role": "user", "content": entry["user"]})
        messages.append({"role": "assistant", "content": entry["agent"]})
    
    # Add current user message
    messages.append({"role": "user", "content": user_input})
    
    # Get AI response with tool calling
    response = await client.chat.completions.create(
        model="anthropic/claude-3.5-sonnet",
        messages=messages,
        max_tokens=1000,
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "fetch_inventory_query",
                    "description": "Search inventory for products. Call this when user mentions any product, chemical, or material.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string", 
                                "description": "Product name, chemical name, or search terms extracted from user message"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_session_memory",
                    "description": "Update session data ONLY when user explicitly confirms both product selection AND request type.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "product_id": {
                                "type": "string",
                                "description": "Exact _id of the confirmed product from inventory results"
                            },
                            "product_name": {
                                "type": "string", 
                                "description": "Exact name_en of the confirmed product"
                            },
                            "product_details": {
                                "type": "object",
                                "description": "FULL product object from inventory results"
                            },
                            "request": {
                                "type": "string",
                                "description": "Request type: 'sample', 'quotation', 'ppr', or 'order' ONLY",
                                "enum": ["sample", "quotation", "ppr", "order"]
                            },
                            "agent": {
                                "type": "string", 
                                "description": "Set to 'request_details' ONLY when handing over to next agent"
                            }
                        },
                        "required": ["product_id", "product_name", "product_details", "request", "agent"]
                    }
                }
            }
        ],
        tool_choice="auto"
    )
    
    message = response.choices[0].message
    response_content = message.content or ""
    tool_calls = message.tool_calls or []
    
    print(f"🧠 AI initial response: {response_content}")
    print(f"🔧 Tool calls requested: {len(tool_calls)}")
    
    # Process tool calls
    session_updates = {}
    
    if tool_calls:
        # Create a new messages array for the follow-up
        follow_up_messages = messages.copy()
        
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            # Add the tool call to messages
            follow_up_messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [tool_call]
            })
            
            if function_name == "fetch_inventory_query":
                # Call inventory API
                query = function_args["query"]
                inventory_result = await fetch_inventory_query(query)
                
                # Add tool result to messages
                follow_up_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(inventory_result, default=str)
                })
                
            elif function_name == "update_session_memory":
                # Collect session updates
                session_updates.update(function_args)
                print(f"💾 AI explicitly updating session: {function_args}")
                
                # Add tool confirmation
                follow_up_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps({"status": "success", "message": "Session updated"})
                })
        
        # Get final AI response with tool results
        final_response_obj = await client.chat.completions.create(
            model="anthropic/claude-3.5-sonnet",
            messages=follow_up_messages,
            max_tokens=800
        )
        final_response = final_response_obj.choices[0].message.content or ""
    else:
        final_response = response_content
    
    return {
        "response": final_response,
        "session_updates": session_updates
    }