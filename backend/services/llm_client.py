"""
Universal LLM Client - 支持多個 LLM 提供商
"""
import os
from typing import Optional, Dict, Any, List
import requests
import json


class UniversalLLMClient:
    """統一的 LLM 客戶端，支持多個提供商"""
    
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "openrouter").lower()
        
        # API Keys
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.grok_api_key = os.getenv("GROK_API_KEY")
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        # Models
        self.google_model = os.getenv("GOOGLE_MODEL", "gemini-pro")
        self.grok_model = os.getenv("GROK_MODEL", "grok-beta")
        self.openrouter_model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-exp:free")
        self.openai_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        
        print(f"✅ LLM Provider: {self.provider}")
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """統一的聊天完成接口"""
        
        if self.provider == "google":
            return self._google_chat(messages, temperature, max_tokens)
        elif self.provider == "grok":
            return self._grok_chat(messages, temperature, max_tokens)
        elif self.provider == "openrouter":
            return self._openrouter_chat(messages, temperature, max_tokens)
        elif self.provider == "openai":
            return self._openai_chat(messages, temperature, max_tokens)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def _google_chat(self, messages: List[Dict], temperature: float, max_tokens: int) -> str:
        """Google AI (Gemini) API"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.google_model}:generateContent?key={self.google_api_key}"
        
        # 轉換消息格式
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        result = response.json()
        return result["candidates"][0]["content"]["parts"][0]["text"]
    
    def _grok_chat(self, messages: List[Dict], temperature: float, max_tokens: int) -> str:
        """Grok API (xAI)"""
        url = "https://api.x.ai/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.grok_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.grok_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        return result["choices"][0]["message"]["content"]
    
    def _openrouter_chat(self, messages: List[Dict], temperature: float, max_tokens: int) -> str:
        """OpenRouter API"""
        import time
        
        url = "https://openrouter.ai/api/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "Document Intelligence Platform"
        }
        
        payload = {
            "model": self.openrouter_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries + 1):
            try:
                response = requests.post(url, headers=headers, json=payload)
                
                if response.status_code == 429:
                    if attempt < max_retries:
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        response.raise_for_status()
                
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
                
            except requests.exceptions.HTTPError as e:
                # If it's a 429 but we've exhausted retries or some other error
                if response.status_code == 429:
                     raise Exception(f"OpenRouter Rate Limit Exceeded after {max_retries} retries. Please try again later.")
                raise e
            except Exception as e:
                if attempt < max_retries:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                raise e
        
        raise Exception("Failed to get response from OpenRouter")
    
    def _openai_chat(self, messages: List[Dict], temperature: float, max_tokens: int) -> str:
        """OpenAI API"""
        from openai import OpenAI
        
        client = OpenAI(api_key=self.openai_api_key)
        
        response = client.chat.completions.create(
            model=self.openai_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content
    
    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """創建文本嵌入（目前僅支持 OpenAI 和 OpenRouter）"""
        
        if self.provider == "openrouter":
            # OpenRouter 支持嵌入模型
            url = "https://openrouter.ai/api/v1/embeddings"
            
            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json"
            }
            
            all_embeddings = []
            batch_size = 100
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                
                payload = {
                    "model": "text-embedding-3-small",  # OpenRouter 支持 OpenAI 嵌入模型
                    "input": batch
                }
                
                response = requests.post(url, headers=headers, json=payload)
                response.raise_for_status()
                
                result = response.json()
                embeddings = [item["embedding"] for item in result["data"]]
                all_embeddings.extend(embeddings)
            
            return all_embeddings
        
        elif self.provider == "openai":
            from openai import OpenAI
            
            client = OpenAI(api_key=self.openai_api_key)
            
            all_embeddings = []
            batch_size = 100
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                
                response = client.embeddings.create(
                    model="text-embedding-3-small",
                    input=batch
                )
                
                embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(embeddings)
            
            return all_embeddings
        
        else:
            # 對於不支持嵌入的提供商，使用簡單的文本哈希作為替代
            # 這不是真正的語義嵌入，但可以作為臨時解決方案
            print(f"⚠️ Warning: {self.provider} doesn't support embeddings, using fallback")
            import hashlib
            import numpy as np
            
            embeddings = []
            for text in texts:
                # 使用文本哈希創建偽嵌入
                hash_obj = hashlib.sha256(text.encode())
                hash_bytes = hash_obj.digest()
                # 轉換為 1536 維向量（與 OpenAI 嵌入維度匹配）
                embedding = np.frombuffer(hash_bytes * 48, dtype=np.float32)[:1536].tolist()
                embeddings.append(embedding)
            
            return embeddings


# 全局客戶端實例
llm_client = UniversalLLMClient()
