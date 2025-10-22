import json
from typing import Dict, Any
from core.n8n_agent import HTTPTool
from core.config import settings

class ProductSearchTool(HTTPTool):
    """Specialized tool for product search"""
    
    def __init__(self):
        base_headers = {
            "Content-Type": "application/json",
            "x-user-type": "Buyer",
            "x-auth-language": "English"
        }
        super().__init__(base_headers=base_headers)
        self.name = "product_search"
        self.description = "Search for chemical products in the inventory database"
    
    async def _arun(self, query: str) -> str:
        """Search products with the given query"""
        payload = {"query": query}
        result = await super()._arun(
            url=settings.PRODUCT_SEARCH_URL,
            method="PATCH",
            body=payload
        )
        return result

class MemoryTool:
    """Tool for reading/writing session memory"""
    
    def __init__(self, session_storage):
        self.session_storage = session_storage
        self.name = "session_memory"
        self.description = "Read and write data to session memory for persistence across conversations"
    
    async def read_memory(self, session_id: str) -> Dict[str, Any]:
        """Read session memory"""
        return await self.session_storage.get_session(session_id)
    
    async def write_memory(self, session_id: str, updates: Dict[str, Any]):
        """Write to session memory"""
        await self.session_storage.update_session_state(session_id, updates)
    
    async def update_request_state(self, session_id: str, new_state: str):
        """Update the request state in memory"""
        await self.session_storage.update_session_state(session_id, {
            "request": new_state
        })

class ProductSelectionTool:
    """Tool for handling product selection logic"""
    
    def __init__(self, memory_tool: MemoryTool):
        self.memory_tool = memory_tool
        self.name = "product_selection"
        self.description = "Handle product selection and confirmation logic"
    
    def format_products(self, products_data: str) -> str:
        """Format products from API response"""
        try:
            data = json.loads(products_data)
            products = data.get("results", {}).get("products", [])
            
            if not products:
                return "No products found matching your search."
            
            formatted = "**🎯 I found these products:**\n\n"
            for i, product in enumerate(products, 1):
                name = product.get('name_en', 'N/A')
                brand = product.get('brand_en', 'N/A')
                product_id = product.get('_id', 'N/A')[:8]
                price = product.get('price', 'N/A')
                min_qty = product.get('minQuantity', 'N/A')
                
                formatted += f"**{i}. {name}** - {brand} | Price: ${price} | Min Qty: {min_qty} | ID: {product_id}\n"
            
            formatted += "\n**Please select a product by number (1, 2, 3...) or describe which one you want.**"
            return formatted
            
        except Exception as e:
            return f"Error formatting products: {str(e)}"
    
    def get_product_by_selection(self, products_data: str, selection: str) -> Dict[str, Any]:
        """Get product based on user selection"""
        try:
            data = json.loads(products_data)
            products = data.get("results", {}).get("products", [])
            
            # Check for number selection
            if selection.isdigit():
                index = int(selection) - 1
                if 0 <= index < len(products):
                    return products[index]
            
            # Check for text matching
            selection_lower = selection.lower()
            for product in products:
                name = product.get('name_en', '').lower()
                brand = product.get('brand_en', '').lower()
                
                if (selection_lower in name or selection_lower in brand or 
                    name in selection_lower or brand in selection_lower):
                    return product
            
            return None
            
        except Exception as e:
            print(f"Product selection error: {e}")
            return None