# agents/request_details.py
import asyncio
import json
import re
from datetime import datetime, timedelta
from openai import AsyncOpenAI

# Initialize Async client for OpenRouter
client = AsyncOpenAI(
    api_key="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",
    base_url="https://openrouter.ai/api/v1"
)

async def handle_request_details(user_input: str, session_data: dict):
    """
    Agent 2: Request Details Handler - Collects and validates all request details
    """
    try:
        # Check if we should hand over
        if session_data.get("agent") != "request_details":
            return "I'll hand you over to the next specialist.", session_data
        
        # Process with AI using validation tools
        ai_response = await process_request_details(user_input, session_data)
        
        # Update session from AI's tool calls
        if "session_updates" in ai_response:
            for key, value in ai_response["session_updates"].items():
                if value is not None:
                    session_data["product_details"][key] = value
                    print(f"💾 Updated field: {key} = {value}")
            
            # Check if all fields are completed and hand over
            if ai_response.get("handover_ready", False):
                session_data["agent"] = "address_purpose"
                print("🚀 All fields completed - handing over to agent 3")
        
        # Add to history
        session_data.setdefault("history", []).append({
            "user": user_input, 
            "agent": ai_response["response"]
        })
        
        return ai_response["response"], session_data
        
    except Exception as e:
        print(f"❌ Error in handle_request_details: {e}")
        error_msg = "I apologize, but I'm having trouble processing your request. Please try again."
        session_data.setdefault("history", []).append({
            "user": user_input,
            "agent": error_msg
        })
        return error_msg, session_data

async def process_request_details(user_input: str, session_data: dict):
    """
    Process request details with validation tools
    """
    request_type = session_data.get("request", "").lower()
    product_details = session_data.get("product_details", {})
    
    # Get required fields for this request type
    required_fields = get_required_fields(request_type)
    completed_fields = get_completed_fields(product_details, required_fields)
    pending_fields = [f for f in required_fields if f not in completed_fields]
    
    # Build system prompt
    system_prompt = build_system_prompt(session_data, required_fields, completed_fields, pending_fields)
    
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    # Add conversation history
    history = session_data.get("history", [])
    for entry in history[-6:]:
        messages.append({"role": "user", "content": entry["user"]})
        messages.append({"role": "assistant", "content": entry["agent"]})
    
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
                    "name": "validate_quantity",
                    "description": "Validate quantity against product limits",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "quantity": {
                                "type": "number",
                                "description": "Quantity value to validate"
                            }
                        },
                        "required": ["quantity"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "validate_date",
                    "description": "Validate delivery date is in the future",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "delivery_date": {
                                "type": "string",
                                "description": "Date in YYYY-MM-DD format"
                            }
                        },
                        "required": ["delivery_date"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "validate_selection",
                    "description": "Validate selection from allowed options",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "field_name": {
                                "type": "string",
                                "description": "Name of the field",
                                "enum": ["unit", "incoterm", "mode_of_payment", "packaging_pref"]
                            },
                            "selected_value": {
                                "type": "string",
                                "description": "Selected value to validate"
                            }
                        },
                        "required": ["field_name", "selected_value"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate_expected_price",
                    "description": "Calculate expected price from quantity and price per unit",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "quantity": {
                                "type": "number",
                                "description": "Quantity value"
                            },
                            "price_per_unit": {
                                "type": "number",
                                "description": "Price per unit value"
                            }
                        },
                        "required": ["quantity", "price_per_unit"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_field",
                    "description": "Update a field value after validation",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "field_name": {
                                "type": "string",
                                "description": "Name of the field to update"
                            },
                            "field_value": {
                                "type": "string",
                                "description": "Validated value to store"
                            }
                        },
                        "required": ["field_name", "field_value"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_completion_status",
                    "description": "Check if all required fields are completed",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "completed_fields": {
                                "type": "array",
                                "description": "List of completed field names",
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["completed_fields"]
                    }
                }
            }
        ],
        tool_choice="auto"
    )
    
    message = response.choices[0].message
    response_content = message.content or ""
    tool_calls = message.tool_calls or []
    
    print(f"🧠 AI response: {response_content}")
    print(f"🔧 Tool calls: {len(tool_calls)}")
    
    # Process tool calls
    session_updates = {}
    handover_ready = False
    
    if tool_calls:
        follow_up_messages = messages.copy()
        
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            follow_up_messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [tool_call]
            })
            
            if function_name == "validate_quantity":
                result = validate_quantity(function_args, product_details)
                follow_up_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result)
                })
                
            elif function_name == "validate_date":
                result = validate_date(function_args)
                follow_up_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result)
                })
                
            elif function_name == "validate_selection":
                result = validate_selection(function_args)
                follow_up_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result)
                })
                
            elif function_name == "calculate_expected_price":
                result = calculate_expected_price(function_args)
                follow_up_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result)
                })
                
            elif function_name == "update_field":
                session_updates[function_args["field_name"]] = function_args["field_value"]
                follow_up_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps({"status": "success"})
                })
                
            elif function_name == "check_completion_status":
                result = check_completion_status(function_args, required_fields)
                handover_ready = result.get("all_completed", False)
                follow_up_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result)
                })
        
        # Get final response
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
        "session_updates": session_updates,
        "handover_ready": handover_ready
    }

# Validation Functions
def validate_quantity(args: dict, product_details: dict) -> dict:
    """Validate quantity against product limits"""
    quantity = args["quantity"]
    min_quantity = product_details.get("minQuantity", 1)
    available_quantity = product_details.get("quantity", float('inf'))
    
    if quantity < min_quantity:
        return {
            "is_valid": False,
            "message": f"Quantity must be at least {min_quantity} (minimum order quantity)",
            "suggested_min": min_quantity
        }
    elif quantity > available_quantity:
        return {
            "is_valid": False,
            "message": f"Quantity exceeds available stock of {available_quantity}",
            "suggested_max": available_quantity
        }
    else:
        return {
            "is_valid": True,
            "message": f"Quantity {quantity} is valid (min: {min_quantity}, max: {available_quantity})"
        }

def validate_date(args: dict) -> dict:
    """Validate delivery date is in the future"""
    delivery_date_str = args["delivery_date"]
    today = datetime.now().date()
    
    try:
        delivery_date = datetime.strptime(delivery_date_str, "%Y-%m-%d").date()
        if delivery_date <= today:
            return {
                "is_valid": False,
                "message": f"Delivery date must be after today ({today.strftime('%Y-%m-%d')})",
                "today": today.strftime("%Y-%m-%d")
            }
        else:
            return {
                "is_valid": True,
                "message": f"Delivery date {delivery_date_str} is valid"
            }
    except ValueError:
        return {
            "is_valid": False,
            "message": "Invalid date format. Please use YYYY-MM-DD format"
        }

def validate_selection(args: dict) -> dict:
    """Validate selection from allowed options"""
    field_name = args["field_name"]
    selected_value = args["selected_value"]
    
    options_map = {
        "unit": ["KG", "TON"],
        "incoterm": ["Ex Factory", "Deliver to Buyer Factory"],
        "mode_of_payment": ["LC", "TT", "Cash"],
        "packaging_pref": ["Bulk Tanker", "PP Bag", "Jerry Can", "Drum"]
    }
    
    allowed_options = options_map.get(field_name, [])
    
    if selected_value in allowed_options:
        return {
            "is_valid": True,
            "message": f"Selected {selected_value} is valid for {field_name}",
            "allowed_options": allowed_options
        }
    else:
        return {
            "is_valid": False,
            "message": f"Invalid selection for {field_name}. Allowed options: {', '.join(allowed_options)}",
            "allowed_options": allowed_options
        }

def calculate_expected_price(args: dict) -> dict:
    """Calculate expected price from quantity and price per unit"""
    try:
        quantity = float(args["quantity"])
        price_per_unit = float(args["price_per_unit"])
        expected_price = quantity * price_per_unit
        
        return {
            "calculated_value": expected_price,
            "formula": f"{quantity} × {price_per_unit} = {expected_price}",
            "status": "success"
        }
    except (ValueError, TypeError) as e:
        return {
            "calculated_value": 0,
            "error": "Invalid input values for calculation",
            "status": "error"
        }

def check_completion_status(args: dict, required_fields: list) -> dict:
    """Check if all required fields are completed"""
    completed_fields = args["completed_fields"]
    pending_fields = [f for f in required_fields if f not in completed_fields]
    
    return {
        "all_completed": len(pending_fields) == 0,
        "completed_count": len(completed_fields),
        "total_required": len(required_fields),
        "pending_fields": pending_fields
    }

# Helper Functions
def get_required_fields(request_type: str) -> list:
    """Get required fields based on request type"""
    base_fields = ["unit", "quantity", "price_per_unit", "expected_price"]
    
    if request_type in ["order", "sample", "quotation"]:
        base_fields.extend(["phone", "incoterm", "mode_of_payment", "packaging_pref"])
    
    if request_type in ["order", "sample", "ppr"]:
        base_fields.append("delivery_date")
    
    return base_fields

def get_completed_fields(product_details: dict, required_fields: list) -> list:
    """Get list of completed fields"""
    return [field for field in required_fields if product_details.get(field) not in [None, ""]]

def build_system_prompt(session_data: dict, required_fields: list, completed_fields: list, pending_fields: list) -> str:
    """Build comprehensive system prompt"""
    request_type = session_data.get("request", "").upper()
    product_details = session_data.get("product_details", {})
    
    prompt = f"""You are a **Request Details Specialist** for chemical product orders.
Your job is to collect and validate all required details for a {request_type} request.

PRODUCT INFORMATION:
- Product: {session_data.get('product_name', 'N/A')}
- Available Stock: {product_details.get('quantity', 'N/A')}
- Minimum Order: {product_details.get('minQuantity', 'N/A')}
- Current Unit: {product_details.get('unit', 'N/A')}

REQUIRED FIELDS for {request_type}:
{format_fields_info(required_fields)}

VALIDATION RULES:
1. **Quantity**: Must be ≥ {product_details.get('minQuantity', 1)} and ≤ {product_details.get('quantity', 'available stock')}
2. **Delivery Date**: Must be after {datetime.now().strftime('%Y-%m-%d')} (use YYYY-MM-DD format)
3. **Selections**: Must choose from provided options only
4. **Numbers**: Must be positive numbers only
5. **Price Calculation**: Expected price = Quantity × Price per unit (calculated automatically)

FIELD OPTIONS:
- Unit: KG, TON
- Incoterm: Ex Factory, Deliver to Buyer Factory  
- Payment: LC, TT, Cash
- Packaging: Bulk Tanker, PP Bag, Jerry Can, Drum

CURRENT PROGRESS:
✅ Completed: {len(completed_fields)}/{len(required_fields)} fields
{format_progress(completed_fields, pending_fields, product_details)}

COLLECTION STRATEGY:
1. Start by listing missing fields if this is the first interaction
2. Ask for one field at a time with clear options for selections
3. Use validation tools for EVERY field input
4. Confirm values before storing
5. Calculate expected price automatically
6. When all fields are complete, check completion status and hand over

TOOLS AVAILABLE:
- validate_quantity: Check quantity against stock limits
- validate_date: Ensure delivery date is future
- validate_selection: Verify selection from allowed options  
- calculate_expected_price: Compute total price
- update_field: Store validated field value
- check_completion_status: Verify all fields are complete

After collecting ALL required fields and validating them, use check_completion_status and hand over to the next agent."""

    return prompt

def format_fields_info(required_fields: list) -> str:
    """Format field information for prompt"""
    field_descriptions = {
        "unit": "Unit of measurement (KG or TON)",
        "quantity": f"Quantity required (number)",
        "price_per_unit": "Your offered price per unit (number)",
        "expected_price": "Total expected price (auto-calculated)",
        "phone": "Contact phone number",
        "incoterm": "Delivery terms (Ex Factory or Deliver to Buyer Factory)",
        "mode_of_payment": "Payment method (LC, TT, or Cash)",
        "packaging_pref": "Packaging preference (Bulk Tanker, PP Bag, Jerry Can, or Drum)",
        "delivery_date": f"Delivery date (after {datetime.now().strftime('%Y-%m-%d')})"
    }
    
    return "\n".join([f"- {field}: {field_descriptions.get(field, field)}" for field in required_fields])

def format_progress(completed_fields: list, pending_fields: list, product_details: dict) -> str:
    """Format progress information"""
    lines = []
    
    if completed_fields:
        lines.append("Completed fields:")
        for field in completed_fields:
            value = product_details.get(field, "")
            lines.append(f"  ✓ {field}: {value}")
    
    if pending_fields:
        lines.append("Pending fields:")
        for field in pending_fields:
            lines.append(f"  □ {field}")
    
    return "\n".join(lines)

# TODO: Add phone number validation for different countries
# def validate_phone_number(phone: str) -> dict:
#     """Validate phone number format (to be implemented later)"""
#     # Basic validation - can be enhanced for different countries
#     if re.match(r'^\+?[\d\s\-\(\)]{10,}$', phone):
#         return {"is_valid": True, "message": "Phone number format is valid"}
#     else:
#         return {"is_valid": False, "message": "Invalid phone number format"}