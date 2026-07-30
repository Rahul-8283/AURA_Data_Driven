# Phase 6: LLM Property Prediction (Detailed Implementation Plan)

## 1. Objective and Scope
Once the Genetic Algorithm creates a new population of mathematically valid but untested mutated battery materials (Phase 5), we must evaluate how "good" they are. Instead of training a complex, brittle Machine Learning regression model from scratch, we will use a top-tier LLM (via OpenRouter) instructed to act as a computational material scientist. This logic resides in the LangGraph `predictor_node`.

---

## 2. OpenRouter API Integration (`app/services/llm/client.py`)

### 2.1 Async Client Setup
Because we have to evaluate 20 materials per generation, and the GA runs for 20 generations, we will make 400 API calls per discovery run. Sequential calls would take hours. We MUST use asynchronous calls.
- Import the standard `openai` Python package.
- Configure the `AsyncOpenAI` client to point to OpenRouter.
```python
from openai import AsyncOpenAI
from app.core.config import settings

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.OPENROUTER_API_KEY,
)
```

### 2.2 Retry & Timeout Wrappers
- Create a reusable wrapper function `predict_properties_async(material_composition: str, context: str)`.
- Use the `tenacity` library to implement `@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))`.
- If OpenRouter times out or returns a 502 Bad Gateway (common with high concurrency), the wrapper will automatically wait and retry.

---

## 3. Prompt Engineering & GraphRAG Context Injection

The LLM is highly prone to hallucination. To prevent this, we must inject the solid literature evidence we gathered via the GraphRAG engine (Phase 3).

### 3.1 System Prompt Design
Craft a highly constrained, strict system prompt.
- **Role:** *"You are an expert computational battery chemist. You do not hallucinate."*
- **Task:** *"Estimate the specific capacity (mAh/g), nominal voltage (V), cycle life, and cost impact of the provided battery material composition."*
- **Constraint:** *"You MUST base your prediction primarily on the provided GraphRAG literature context. If the context states that Al doping reduces capacity but increases thermal stability, your numerical predictions MUST reflect a drop in capacity and a rise in cycle life compared to standard baselines."*

### 3.2 Output Formatting (Strict JSON schema)
We need numerical values to calculate fitness scores later. The LLM must return strict, parseable JSON.
- Instruct the LLM to output a precise JSON structure.
- Use `response_format={"type": "json_object"}` in the OpenRouter API call.
- Define a strict Pydantic schema to validate the LLM's output. If the LLM returns `"high"` instead of `250.0`, Pydantic will throw a validation error.
```python
from pydantic import BaseModel, Field

class PredictionResult(BaseModel):
    specific_capacity: float = Field(..., description="Estimated capacity in mAh/g")
    voltage: float = Field(..., description="Nominal voltage in V")
    cycle_life: int = Field(..., description="Estimated cycles to 80% retention")
    cost_estimate_usd_kg: float = Field(..., description="Estimated material cost per kg")
    reasoning: str = Field(..., description="A 2-sentence chemical explanation for these numbers based ONLY on the context.")
```

---

## 4. The Predictor Node Logic (`app/agents/nodes/predictor.py`)

Implement the LangGraph node execution that ties the GraphRAG and LLM prediction together.
1. Read the `current_population` from the `ResearchState`.
2. **Fetch Context Concurrently:**
   - For each material in the population, create an async task calling the GraphRAG Engine (Phase 3) with the prompt: *"What are the electrochemical properties and degradation modes of {material}?"*
   - Use `asyncio.gather` to fetch all 20 contexts simultaneously.
3. **Run Predictions Concurrently:**
   - Pass the material composition and its unique GraphRAG context to the OpenRouter LLM via `predict_properties_async`.
   - Use `asyncio.gather` again to run all 20 LLM predictions simultaneously.
4. **Validation and State Update:**
   - Parse each JSON response through the Pydantic `PredictionResult` schema.
   - Attach the validated predicted properties (`capacity`, `voltage`, `cost`, `reasoning`) directly to the material dictionary in the population list.
   - Update the `ResearchState` with the newly annotated `current_population` and append a progress log.

---

## 5. Execution and Verification Checklist

1. **Standalone Test:** Write a test script passing a well-known baseline material (e.g., `LiNi0.8Co0.1Mn0.1O2`) to the prediction function with relevant context.
2. **Format Verification:** Verify that the OpenRouter API reliably returns a valid JSON object.
3. **Type Safety:** Parse the JSON through the Pydantic schema to ensure type safety (e.g., capacity is parsed as a float, not a string or a range like "180-200").
4. **Reasoning Check:** Verify the `reasoning` field provides a logical chemical explanation that directly references the injected context (e.g., "Due to the high nickel content mentioned in the structural rules, capacity is high but cycle life is reduced due to cation mixing").
5. **Concurrency Profiling:** Run the full `predictor_node` with 20 dummy materials. Ensure parallel execution (`asyncio.gather`) processes all 20 items and completes the node execution in under 30 seconds. If it takes longer, adjust concurrency limits or switch to a faster OpenRouter model (e.g., Claude 3 Haiku).
