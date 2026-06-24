import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from typing import List, Dict
import sqlite3


class NarrativeEngine:
    def __init__(self, model_name: str = "meta-llama/Llama-3.1-8B-Instruct", device: str = "auto"):
        """
        Initialize with Hugging Face model.
        For CPU: device="cpu", load_in_8bit=True
        For GPU: device="cuda", load_in_4bit=True
        """
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            device_map=device,
            load_in_8bit=(device == "cpu")
        )
        self.pipe = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            max_new_tokens=150,
            temperature=0.7,
            top_p=0.9,
            do_sample=True
        )
        self.db = sqlite3.connect("asford.db")
        self.db.row_factory = sqlite3.Row

    def retrieve_context(self, entities: List[str], year: int, top_n: int = 5) -> List[Dict]:
        """
        RAG: Retrieve relevant memory blocks for LLM context.
        Queries llm_context table, filters by entity + year, ranks by importance.
        """
        placeholders = ','.join('?' * len(entities))
        query = f"""
            SELECT * FROM llm_context 
            WHERE entities LIKE ? AND year <= ?
            ORDER BY importance DESC, year DESC
            LIMIT ?
        """
        results = []
        for entity in entities:
            cursor = self.db.execute(query, (f"%{entity}%", year, top_n))
            results.extend([dict(row) for row in cursor.fetchall()])

        seen = set()
        unique = []
        for r in results:
            if r["id"] not in seen:
                seen.add(r["id"])
                unique.append(r)

        return sorted(unique, key=lambda x: x["importance"], reverse=True)[:top_n]

    def build_prompt(self, event_context: str, entities: List[str], year: int, quarter: int) -> str:
        """Build structured prompt from database context"""
        memories = self.retrieve_context(entities, year)

        context_blocks = [f"- {mem['content']}" for mem in memories]
        context_str = "\n".join(context_blocks) if context_blocks else "No prior context."

        prompt = f"""You are an objective, unsentimental game master. No cheering. No ensuring victory. The world is indifferent.

GAME STATE (Year {year}, Q{quarter}):
{event_context}

RELEVANT MEMORY:
{context_str}

INSTRUCTIONS:
Write 2-3 sentences of narrative texture. Cold, specific, human. No lists. No dashboards. Show, don't tell. Include one sensory detail (smell, sound, temperature). If a character speaks, let their words reveal their motivation, not explain it.

NARRATIVE:"""
        return prompt

    def generate_texture(self, event_context: str, entities: List[str], year: int, quarter: int) -> str:
        """Generate narrative texture via local LLM"""
        prompt = self.build_prompt(event_context, entities, year, quarter)
        output = self.pipe(prompt, return_full_text=False)
        generated = output[0]["generated_text"].strip()

        if "\n\n" in generated:
            generated = generated.split("\n\n")[0]

        self.log_narrative(year, quarter, event_context, generated, entities)
        return generated

    def log_narrative(self, year: int, quarter: int, context: str, text: str, entities: List[str]):
        """Store generated narrative for recall"""
        self.db.execute(
            """
            INSERT INTO narrative_log (year, quarter, context, narrative_text, entities_involved)
            VALUES (?, ?, ?, ?, ?)
            """,
            (year, quarter, context, text, ",".join(entities)),
        )
        self.db.commit()
