import requests
from typing import List, Dict
import os

class NarrativeEngine:
    def __init__(self, model_name: str = "meta-llama/Llama-3.1-8B-Instruct"):
        """
        Initialize with Hugging Face Inference API.
        Requires HF_TOKEN environment variable.
        """
        self.model_name = model_name
        self.api_url = f"https://api-inference.huggingface.co/models/{model_name}"
        self.headers = {"Authorization": f"Bearer {os.getenv('HF_TOKEN', '')}"}
    
    def build_prompt(self, financial_data: Dict, directives: List[str], year: int) -> str:
        """Build structured prompt from financial data"""
        directives_str = "\n".join([f"- {d}" for d in directives]) if directives else "No directives."
        
        prompt = f"""You are an objective, unsentimental game master. No cheering. No ensuring victory. The world is indifferent.

YEAR {year} FINANCIAL RESULTS:
Revenue: ${financial_data['revenue']:,.0f}
EBITDA: ${financial_data['ebitda']:,.0f} ({financial_data['ebitda_margin']:.1f}% margin)
Net Income: ${financial_data['net_income']:,.0f}
Cash Position: ${financial_data['cash']:,.0f}
Total Debt: ${financial_data['debt']:,.0f}
Debt Service Coverage Ratio: {financial_data['dscr']:.2f}x
Covenant Breach: {'YES - Bank may accelerate debt' if financial_data['covenant_breach'] else 'No'}

PLAYER DIRECTIVES:
{directives_str}

INSTRUCTIONS:
Write 2-3 sentences of narrative texture. Cold, specific, human. No lists. No dashboards. Show, don't tell. Include one sensory detail (smell, sound, temperature). If a character speaks, let their words reveal their motivation, not explain it.

NARRATIVE:"""
        return prompt
    
    def generate_texture(self, financial_data: Dict, directives: List[str], year: int) -> str:
        """Generate narrative texture via Hugging Face LLM"""
        prompt = self.build_prompt(financial_data, directives, year)
        
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json={
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": 200,
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "do_sample": True
                    }
                },
                timeout=30
            )
            
            if response.status_code != 200:
                return f"Error calling Hugging Face API: {response.status_code} - {response.text}"
            
            result = response.json()
            
            # Handle different response formats
            if isinstance(result, list) and len(result) > 0:
                generated = result[0].get("generated_text", "").strip()
            elif isinstance(result, dict):
                generated = result.get("generated_text", "").strip()
            else:
                generated = str(result).strip()
            
            # Clean up the response (remove the prompt)
            if prompt in generated:
                generated = generated.replace(prompt, "").strip()
            
            # Truncate to first 2-3 sentences
            sentences = generated.split(". ")
            if len(sentences) > 3:
                generated = ". ".join(sentences[:3]) + "."
            
            return generated if generated else "The year passed in silence."
        
        except requests.exceptions.Timeout:
            return "The year passed. The model was slow to respond."
        except Exception as e:
            return f"The year passed. (Error: {str(e)})"

