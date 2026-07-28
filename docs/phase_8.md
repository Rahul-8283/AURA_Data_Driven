# Phase 8: LLM Property Prediction (Detailed Implementation Plan)

## 1. Objective and Scope
Once the Genetic Algorithm creates a new population of mutated battery materials (Phase 7), we must evaluate how "good" they are. Instead of training a complex ML model from scratch, we will use a top-tier LLM (via OpenRouter) instructed to act as a computational material scientist. This logic resides in the LangGraph `predictor_node`.

---

## 2. OpenRouter API Integration (`app/services/llm/client.py`)

### 2.1 Setup
- Import the standard `openai` Python package.
- Configure the client to point to OpenRouter.
```python
from openai import AsyncOpenAI
from app.core.config import settings

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.OPENROUTER_API_KEY,
)
```
- Create a reusable wrapper function `predict_properties(material_composition: str, context: str)` that handles API retries and timeout errors.

---

## 3. Prompt Engineering & GraphRAG Injection

The LLM is prone to hallucination. To prevent this, we must inject the solid literature evidence we gathered via GraphRAG (Phase 5).

### 3.1 System Prompt Design
Craft a highly constrained system prompt.
- **Role:** *"You are an expert computational battery chemist."*
- **Task:** *"Estimate the specific capacity (mAh/g), nominal voltage (V), cycle life, and cost impact of the provided battery material composition."*
- **Constraint:** *"You MUST base your prediction on the provided GraphRAG literature context. Do not invent properties. If a dopant in the composition is known to reduce capacity but increase stability based on the context, adjust your numbers accordingly."*

### 3.2 Output Formatting (Strict JSON)
We need numerical values to calculate fitness scores later. The LLM must return JSON.
- Instruct the LLM to output a precise JSON structure.
- Use `response_format={"type": "json_object"}` in the API call.
- Define a Pydantic schema to validate the output:
```python
from pydantic import BaseModel

class PredictionResult(BaseModel):
    specific_capacity: float
    voltage: float
    cycle_life: int
    cost_estimate_usd_kg: float
    reasoning: str
```

---

## 4. The Predictor Node Logic (`app/agents/nodes/predictor.py`)

Implement the LangGraph node execution.
1. Read the `current_population` from the `ResearchState`.
2. For each material in the population:
   - Call the GraphRAG Engine (Phase 5) with the prompt: *"What are the electrochemical properties of {material}?"*
   - Pass the material composition and the GraphRAG context to the LLM via OpenRouter.
   - Parse the JSON response.
   - Attach the predicted properties (`capacity`, `voltage`, etc.) directly to the material dictionary in the population list.
3. **Async Batching:** Make sure to use `asyncio.gather` to predict properties for the entire population of 20 materials concurrently to save time.
4. Update the `ResearchState` with the newly annotated `current_population`.

---

## 5. Execution and Verification Checklist
1. Write a standalone test script passing a known material (e.g., `LiNi0.8Co0.1Mn0.1O2`) to the prediction function with relevant context.
2. Verify that the OpenRouter API returns a valid JSON object.
3. Parse the JSON through the Pydantic `PredictionResult` schema to ensure type safety (e.g., capacity is a float, not a string).
4. Verify the `reasoning` field provides a logical chemical explanation based on the injected context.
5. Ensure parallel execution (`asyncio.gather`) processes 20 items in under 30 seconds to prevent API timeouts.
