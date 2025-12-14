"""
AI Extraction Service - uses LLM to extract structured data from documents
"""
import json
from typing import Dict, Any, Optional, Tuple
from config import settings
import time
from services.llm_client import llm_client


class AIExtractor:
    """Extract structured metadata from documents using LLM"""
    
    def __init__(self):
        self.client = llm_client
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.max_tokens
    
    def extract_metadata(
        self,
        text: str,
        document_type: str = "general",
        custom_schema: Optional[Dict] = None
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        """
        Extract structured metadata from document text
        
        Args:
            text: Document text content
            document_type: Type of document (contract, sop, etc.)
            custom_schema: Optional custom extraction schema
            
        Returns:
            Tuple of (extracted_metadata, error_message)
        """
        try:
            # Get extraction schema
            schema = custom_schema or self._get_default_schema(document_type)
            
            # Build prompts
            system_prompt = self._build_system_prompt(schema)
            user_prompt = self._build_user_prompt(text, schema)
            
            # Call LLM with retry logic
            response = self._call_llm_with_retry(system_prompt, user_prompt)
            
            # Parse JSON response
            metadata = self._parse_llm_response(response)
            
            # Validate against schema
            validated_metadata = self._validate_metadata(metadata, schema)
            
            return validated_metadata, None
            
        except Exception as e:
            return {}, f"Extraction error: {str(e)}"
    
    def _get_default_schema(self, document_type: str) -> Dict:
        """Get default extraction schema for document type"""
        
        base_fields = [
            {"name": "title", "type": "string", "description": "Document title"},
            {"name": "date", "type": "string", "description": "Document date (ISO format)"},
            {"name": "summary", "type": "string", "description": "Brief summary (max 200 chars)"},
        ]
        
        if document_type == "contract":
            return {
                "fields": base_fields + [
                    {"name": "parties", "type": "array", "description": "List of contracting parties"},
                    {"name": "contract_amounts", "type": "array", "description": "Contract amounts with currency"},
                    {"name": "effective_date", "type": "string", "description": "Contract effective date"},
                    {"name": "expiry_date", "type": "string", "description": "Contract expiry date"},
                    {"name": "key_terms", "type": "array", "description": "Key contract terms"},
                ]
            }
        elif document_type == "sop":
            return {
                "fields": base_fields + [
                    {"name": "department", "type": "string", "description": "Responsible department"},
                    {"name": "version", "type": "string", "description": "SOP version number"},
                    {"name": "approval_date", "type": "string", "description": "Approval date"},
                    {"name": "sections", "type": "array", "description": "Main section titles"},
                    {"name": "procedures", "type": "array", "description": "Key procedures"},
                ]
            }
        elif document_type == "official_document":
            return {
                "fields": base_fields + [
                    {"name": "document_number", "type": "string", "description": "Official document number"},
                    {"name": "sender", "type": "string", "description": "Sender organization/person"},
                    {"name": "recipient", "type": "string", "description": "Recipient organization/person"},
                    {"name": "subject", "type": "string", "description": "Document subject"},
                    {"name": "action_required", "type": "string", "description": "Required action if any"},
                ]
            }
        else:
            return {"fields": base_fields}
    
    def _build_system_prompt(self, schema: Dict) -> str:
        """Build system prompt for extraction"""
        return f"""You are a precise document metadata extractor. 
Extract information from documents according to the provided schema.
Output ONLY valid JSON matching the schema. Do not include explanations or markdown.

Schema:
{json.dumps(schema, indent=2)}

Rules:
1. Extract only information explicitly stated in the document
2. Use null for missing fields
3. Format dates as ISO 8601 (YYYY-MM-DD)
4. Be concise and accurate
5. Output must be valid JSON"""
    
    def _build_user_prompt(self, text: str, schema: Dict) -> str:
        """Build user prompt with document text"""
        # Truncate text if too long
        max_length = 8000  # Leave room for schema and response
        if len(text) > max_length:
            text = text[:max_length] + "\n...[truncated]"
        
        field_names = [f["name"] for f in schema["fields"]]
        
        return f"""Extract the following fields from this document:
{', '.join(field_names)}

Document text:
---
{text}
---

Output JSON:"""
    
    def _call_llm_with_retry(
        self,
        system_prompt: str,
        user_prompt: str,
        max_retries: int = 3
    ) -> str:
        """Call LLM with exponential backoff retry"""
        
        for attempt in range(max_retries):
            try:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                
                response = self.client.chat_completion(
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
                
                return response
                
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                
                # Exponential backoff
                wait_time = 2 ** attempt
                time.sleep(wait_time)
    
    def _parse_llm_response(self, response: str) -> Dict:
        """Parse and validate JSON response from LLM"""
        try:
            # Try to parse as JSON
            metadata = json.loads(response)
            return metadata
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            
            # Try to find JSON object
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            
            raise ValueError("Could not parse JSON from LLM response")
    
    def _validate_metadata(self, metadata: Dict, schema: Dict) -> Dict:
        """Validate and clean extracted metadata"""
        validated = {}
        
        for field in schema["fields"]:
            field_name = field["name"]
            field_type = field["type"]
            
            value = metadata.get(field_name)
            
            # Type validation
            if value is not None:
                if field_type == "string" and not isinstance(value, str):
                    value = str(value)
                elif field_type == "array" and not isinstance(value, list):
                    value = [value] if value else []
                elif field_type == "number" and not isinstance(value, (int, float)):
                    try:
                        value = float(value)
                    except:
                        value = None
            
            validated[field_name] = value
        
        return validated


from typing import Tuple
