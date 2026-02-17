"""
External Knowledge RAG Engine
Fetches real-time drug insights from external scientific sources (PubMed, Drugs.com, etc.)
using Google Search (Serper API) when local data is insufficient.
"""

import os
import requests
import json
import logging
import sys
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class ExternalKnowledgeRAG:
    """
    Retrieves and synthesizes drug information from the web
    """
    
    def __init__(self):
        self.serper_api_key = os.getenv('SERPER_API_KEY')
        self.groq_api_key = os.getenv('GROQ_API_KEY')
        
        if not self.serper_api_key:
            logger.warning("⚠️ SERPER_API_KEY not found. Web RAG will not work.")
        
        if not self.groq_api_key:
            logger.warning("⚠️ GROQ_API_KEY not found. Synthesis will not work.")

    def get_drug_insights(self, drug_name: str) -> Dict:
        """
        Get comprehensive insights for a drug using Web RAG or LLM Fallback
        """
        logger.info(f"🔍 Fetching external insights for: {drug_name}")
        
        # 1. Try Search for scientific info
        search_results = self._search_web(drug_name)
        
        # 2. Synthesize with LLM (using search results OR internal knowledge)
        if not search_results:
            logger.warning("⚠️ Web search failed/empty. Falling back to LLM internal knowledge.")
            context = "Web search unavailable. Please rely on your internal medical knowledge base."
        else:
            context = search_results
            
        insights = self._synthesize_insights(drug_name, context)
        return insights

    def _search_web(self, drug_name: str) -> str:
        """
        Search Google for high-quality medical info
        """
        if not self.serper_api_key:
            return ""
            
        url = "https://google.serper.dev/search"
        
        # Targeted query for medical details
        query = f"{drug_name} mechanism of action dosage side effects interactions contraindications scientific review site:nih.gov OR site:mayoclinic.org OR site:drugs.com"
        
        payload = json.dumps({
            "q": query,
            "num": 5  # Top 5 results
        })
        
        headers = {
            'X-API-KEY': self.serper_api_key,
            'Content-Type': 'application/json'
        }
        
        try:
            print(f"[RAG DEBUG] Searching Serper with query: {query}", file=sys.stderr)
            response = requests.request("POST", url, headers=headers, data=payload)
            print(f"[RAG DEBUG] Serper Status Code: {response.status_code}", file=sys.stderr)
            
            if response.status_code != 200:
                print(f"[RAG DEBUG] Serper Error: {response.text}", file=sys.stderr)
                return ""
                
            data = response.json()
            
            # Extract snippets
            snippets = []
            if 'organic' in data:
                for result in data['organic']:
                    title = result.get('title', '')
                    snippet = result.get('snippet', '')
                    link = result.get('link', '')
                    snippets.append(f"Source: {title} ({link})\nContent: {snippet}")
            
            if not snippets:
                print("[RAG DEBUG] No organic results found in Serper response", file=sys.stderr)
                
            return "\n\n".join(snippets)
            
        except Exception as e:
            print(f"[RAG DEBUG] Serper Exception: {e}", file=sys.stderr)
            logger.error(f"❌ Serper search failed: {e}")
            return ""

    def _synthesize_insights(self, drug_name: str, context: str) -> Dict:
        """
        Use Groq (Llama 3) to synthesize search results into structured insights
        """
        if not self.groq_api_key:
            return {"summary": "LLM API key missing"}
            
        from groq import Groq
        client = Groq(api_key=self.groq_api_key)
        
        prompt = f"""
        You are an expert clinical pharmacist. Generate a comprehensive clinical summary for the drug "{drug_name}".
        
        Context/Search Results:
        {context}
        
        Format the output strictly as a JSON object with these fields:
        {{
            "description": "Brief clinical description",
            "mechanism_of_action": "How it works (scientific explanation)",
            "common_side_effects": "List of common side effects",
            "serious_interactions": "Major drug interactions to avoid",
            "contraindications": "When NOT to use this drug",
            "clinical_pearls": "Key advice for patients (e.g., take with food)"
        }}
        
        If context is provided, use it. If context says "Web search unavailable", use your INTERNAL medical knowledge to provide accurate information.
        Do not hallucinate. If you don't know the drug, state "Unknown drug" in the description.
        """
        
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            return json.loads(completion.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"❌ Insight synthesis failed: {e}")
            return {"error": str(e)}

# Global instance
external_rag = ExternalKnowledgeRAG()

def get_external_insights(drug_name):
    return external_rag.get_drug_insights(drug_name)
