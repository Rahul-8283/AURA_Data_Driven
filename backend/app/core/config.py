from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "AURA"
    API_V1_STR: str = "/api/v1"

    # Supabase
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWT_SECRET: str
    
    # LLM/Embeddings
    HF_API_key: str | None = None
    gemini_api_key: str
    OPENROUTER_API_KEY: str | None = None
    
    # Neo4j
    NEO4J_URI: str
    NEO4J_USERNAME: str
    NEO4J_PASSWORD: str

    # Redis/Celery
    REDIS_URL: str

    # LLM result caches (predictions and validity verdicts), kept per worker process
    LLM_CACHE_TTL_SECONDS: int = 3600
    LLM_CACHE_MAX_ENTRIES: int = 5000

    # Genetic algorithm sizing (lower these for quick test runs)
    GA_GENERATIONS: int = 20
    GA_SEED_POPULATION: int = 10
    GA_POPULATION_SIZE: int = 20

    # Literature Harvesters
    NCBI_API_KEY: str | None = None
    CONTACT_EMAIL: str = ""
    # LLM requests one triplet-extraction run may spend (each covers GRAPH_EXTRACTION_GROUP_SIZE chunks).
    # Kept small because the free OpenRouter tier allows only 50 requests a day, shared with discovery runs.
    GRAPH_EXTRACTION_MAX_CALLS: int = 10
    GRAPH_EXTRACTION_GROUP_SIZE: int = 4
    # Off by default: the sweep spends LLM quota and only runs while `celery beat` is running.
    NIGHTLY_HARVEST_ENABLED: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
