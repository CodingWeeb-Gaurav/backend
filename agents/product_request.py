# agents/product_request.py
import asyncio
import json
import ssl
import re

from openai import AsyncOpenAI
import aiohttp
import certifi
import os
from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()

# Initialize Async client for OpenRouter
client = AsyncOpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

# Allowed units for order placement
ALLOWED_UNITS = ["KG", "TON"]

# Global cache for product searches
PRODUCT_CACHE = {}
# Cache for individual product details by ID
PRODUCT_DETAILS_CACHE = {}
# Cache for product list numbering
PRODUCT_LIST_CACHE = {}
# Cache for current product list display
CURRENT_PRODUCT_LIST = []
async def fetch_inventory_query(query: str):
    """
    Fetch products from inventory API - Tool for AI to call with caching
    """
    # Check cache first
    cache_key = query.lower().strip()
    if cache_key in PRODUCT_CACHE:
        cached_result = PRODUCT_CACHE[cache_key]
        # Only use cache if it actually has products
        if cached_result.get("results", {}).get("products"):
            print(f"🔄 Using cached results for: {query}")
            return cached_result
        else:
            print(f"🔄 Cache has empty results for: {query}, making new API call")
            # Remove the bad cache entry
            del PRODUCT_CACHE[cache_key]
    
    print(f"🔍 Fetching from API: {query}")
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
                
                # Only cache if we actually got products
                if result.get("results", {}).get("products"):
                    PRODUCT_CACHE[cache_key] = result
                    
                    # Clear previous list cache
                    PRODUCT_LIST_CACHE.clear()
                    CURRENT_PRODUCT_LIST.clear()
                    
                    # Also cache each product individually by ID for quick lookup
                    valid_products = []
                    for i, product in enumerate(result["results"]["products"]):
                        product_id = product.get("_id")
                        unit = product.get("unit", "Not specified")
                        
                        # Check if unit is allowed
                        if unit.upper() in ALLOWED_UNITS:
                            if product_id:
                                # Store complete product data
                                PRODUCT_DETAILS_CACHE[product_id] = product
                                # Map list number to product ID
                                PRODUCT_LIST_CACHE[str(i + 1)] = product_id
                                CURRENT_PRODUCT_LIST.append(product)
                                
                                print(f"💾 Cached product {i+1}: {product.get('name_en')} -> ID: {product_id}")
                            valid_products.append(product)
                    
                    # Update the result with only valid products
                    result["results"]["products"] = valid_products
                    result["results"]["valid_count"] = len(valid_products)
                    
                    print(f"📊 Cached {len(valid_products)} valid products with list mapping")
                    print(f"📋 Current list mappings: {PRODUCT_LIST_CACHE}")
                else:
                    print("❌ No products found in API response, not caching")
                
                return result
    except Exception as e:
        print(f"❌ API call failed: {e}")
        return {"error": True, "results": {"products": []}}

def get_current_cached_data_for_prompt():
    """
    Get current cached product data formatted for system prompt
    """
    if not CURRENT_PRODUCT_LIST:
        return "No products currently cached. Please search for products first."
    
    # Prepare clean product data for the prompt
    products_data = []
    for i, product in enumerate(CURRENT_PRODUCT_LIST):
        product_info = {
            "list_number": i + 1,
            "name_en": product.get("name_en", "N/A"),
            "brand_en": product.get("brand_en", "N/A"),
            "unit": product.get("unit", "N/A"),
            "minQuantity": product.get("minQuantity", "N/A"),
            "maxQuantity": product.get("maxQuantity", product.get("quantity", "N/A")),  # Handle both fields
            "specification_en": product.get("specification_en", "N/A"),
            "description_en": product.get("description_en", "N/A"),
            "modal": product.get("modal", "N/A"),
            "_id": product.get("_id", "N/A")
        }
        products_data.append(product_info)
    
    return json.dumps(products_data, indent=2, ensure_ascii=False)

def get_product_by_id(product_id: str):
    """
    Get complete product details by ID from cache
    """
    if product_id in PRODUCT_DETAILS_CACHE:
        return PRODUCT_DETAILS_CACHE[product_id]
    return None

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
    Core AI processing with tool calling - Using GPT-4o with optimized caching
    """
    # Build comprehensive system prompt with CURRENT cached data
    system_prompt = build_system_prompt()
    
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
    
    # Get AI response with tool calling using GPT-4o
    response = await client.chat.completions.create(
        model="openai/gpt-4o",
        messages=messages,
        max_tokens=1000,
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "fetch_inventory_query",
                    "description": "Search inventory for NEW products. Only use when user wants to search for different products than what's currently cached.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string", 
                                "description": "Product name or description to search for"
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
                    "description": "Update session data ONLY when user explicitly confirms both product selection AND request type. MUST include complete product_details object with _id field.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "product_id": {
                                "type": "string",
                                "description": "EXACT _id of the confirmed product from cached results"
                            },
                            "product_name": {
                                "type": "string", 
                                "description": "EXACT name_en of the confirmed product from cached results"
                            },
                            "product_details": {
                                "type": "object",
                                "description": "COMPLETE product object from cached results with ALL fields including _id. MUST be the full product object, not just selected fields."
                            },
                            "request": {
                                "type": "string",
                                "description": "Request type: 'sample', 'quotation', 'ppr', or 'order' ONLY",
                                "enum": ["Sample", "Quote", "ppr", "order"]
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
                # Call inventory API with caching
                query = function_args["query"]
                inventory_result = await fetch_inventory_query(query)
                
                # Filter products by allowed units
                if inventory_result.get("results", {}).get("products"):
                    valid_products = []
                    invalid_products = []
                    
                    for product in inventory_result["results"]["products"]:
                        unit = product.get("unit", "Not specified")
                        
                        # Check if unit is allowed
                        if unit.upper() in ALLOWED_UNITS:
                            valid_products.append(product)
                        else:
                            invalid_products.append(product)
                    
                    # Update the result with only valid products
                    inventory_result["results"]["products"] = valid_products
                    inventory_result["results"]["invalid_products"] = invalid_products
                    inventory_result["results"]["valid_count"] = len(valid_products)
                    inventory_result["results"]["invalid_count"] = len(invalid_products)
                    
                    print(f"📊 Filtered results: {len(valid_products)} valid products, {len(invalid_products)} invalid products")
                
                # Add tool result to messages
                follow_up_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(inventory_result, default=str)
                })
                
            elif function_name == "update_session_memory":
                # Validate that product_details contains actual data with _id
                product_details = function_args.get("product_details", {})
                product_id = function_args.get("product_id")
                
                print(f"🔍 Validating product_details for session update:")
                print(f"   - Product ID from args: {product_id}")
                print(f"   - Product details type: {type(product_details)}")
                print(f"   - Product details keys: {list(product_details.keys()) if product_details else 'None'}")
                print(f"   - Has _id: {'_id' in product_details if product_details else False}")
                
                # If product_details is empty or missing _id, try to get it from cache
                if not product_details or "_id" not in product_details:
                    print(f"🔄 Attempting to get product details from cache for ID: {product_id}")
                    cached_product = get_product_by_id(product_id)
                    if cached_product:
                        print(f"✅ Found product in cache, updating product_details")
                        function_args["product_details"] = cached_product
                        product_details = cached_product
                    else:
                        print("❌ Product not found in cache either")
                
                # Final validation
                if not product_details or "_id" not in product_details:
                    print("❌ AI tried to update session with invalid product_details - missing _id")
                    follow_up_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps({
                            "status": "error", 
                            "message": "Invalid product_details - must contain complete product object from API with _id field. Use exact data from cached results."
                        })
                    })
                else:
                    # 🔧 Validate unit before proceeding
                    unit = product_details.get("unit", "").upper()
                    if unit not in ALLOWED_UNITS:
                        error_msg = f"Cannot proceed with product '{product_details.get('name_en')}' - unit '{unit}' is not allowed. Allowed units: {', '.join(ALLOWED_UNITS)}"
                        print(f"❌ {error_msg}")
                        follow_up_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps({"status": "error", "message": error_msg})
                        })
                    else:
                        # Collect session updates
                        session_updates.update(function_args)
                        print(f"💾 AI updating session with product_id: {product_id}")
                        print(f"💾 Product name: {function_args.get('product_name')}")
                        print(f"💾 Request type: {function_args.get('request')}")
                        print(f"💾 Product details validated successfully")
                        
                        # Add tool confirmation
                        follow_up_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps({
                                "status": "success", 
                                "message": "Session updated with complete product data",
                                "product_id": product_id,
                                "product_name": function_args.get('product_name')
                            })
                        })  
        
        # Get final AI response with tool results
        final_response_obj = await client.chat.completions.create(
            model="openai/gpt-4o",
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

def build_system_prompt() -> str:
    """Build system prompt with current cached data included"""
    
    # Get current cached data for the prompt
    cached_data = get_current_cached_data_for_prompt()
    
    system_prompt = f"""You are a conversational product selection assistant. Your goal is to help users find the right product and specify their request type.
You are the first agent in a triple-agent system where you handle product searches and selections. After your completion, you will hand over to the second agent who collects request details by changing the session's agent to "request_details".
CURRENT CACHED PRODUCT DATA:
{cached_data}
if the user gives a new product search query, use the fetch_inventory_query tool to get fresh results. 
you can only take the data of product and request, any other details like quantity price address purpose will be handled by the upcoming agents.
if user tells you the details of quantity, unit, contact details, address, industry or anything else unrelated to product and request you should ignore them and tell the user that those details will be handled by the next agents.

CRITICAL RULES FOR SESSION UPDATES:
- When calling update_session_memory, you MUST provide the COMPLETE product_details object from the cached data above
- The product_details MUST include all fields, especially the _id field
- Do NOT create a new object or modify the fields - use the exact object from cached data
- Find the complete product object by matching product_id or list_number from the cached data
- After updating session to "request_details", you cannot make any changes in selected product or request type. If the user asks to update those, politely refuse and tell them to refresh the session to start a new order.
HOW TO GET COMPLETE PRODUCT_DETAILS FOR SESSION UPDATE:
1. When user confirms a product, note the product_id (e.g., "68f9da20c7fe40d80722c436")
2. Find the matching product in the cached data above by _id field
3. Use that EXACT product object as the product_details parameter
4. Do NOT create a new object with selected fields

EXAMPLE OF CORRECT update_session_memory CALL:
{{
  "product_id": "68f9da20c7fe40d80722c436",
  "product_name": "sulphuric", 
  "product_details": {{
    "_id": "68f9da20c7fe40d80722c436",
    "name_en": "sulphuric",
    "brand_en": "Deco",
    "unit": "KG",
    "minQuantity": 12,
    "maxQuantity": 768,
    "specification_en": "hbwherbwrwirwirhwir",
    "description_en": "sdfsdjnwejjjiherjithjret", 
    "modal": "acsd"
    // ... ALL other fields from cached data
  }},
  "request": "order",
  "agent": "request_details"
}}

CRITICAL: The product_details MUST be the complete object from cached data, not just the displayed fields.

DATA DISPLAY RULES:

WHEN SHOWING PRODUCT LISTS:
- Display ONLY: name_en and brand_en
- Format: "1. name_en - brand_en"

WHEN SHOWING SINGLE PRODUCT DETAILS:
- Display ONLY: name_en, brand_en, unit, specification_en, description_en.
- Display a plain text with these fields clearly labeled but no bold or '**' formatting
WORKFLOW:
1. User selects product → Show single product details with specified 5 fields only in a bulleted list
2. User confirms product and request type → Call update_session_memory with COMPLETE product object
3. Session updated → Hand over to next agent (do not give a session update or any message after updating agent to "request_details" because the next agent will take over immediately)

TOOLS:
- fetch_inventory_query: Only for NEW product searches
- update_session_memory: Only for final confirmation with COMPLETE product object"""

    return system_prompt