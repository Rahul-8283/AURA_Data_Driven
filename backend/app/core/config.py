from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "AURA"
    API_V1_STR: str = "/api/v1"

    # Supabase
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWT_SECRET: str
    
    # ChromaDB
    CHROMA_DATABASE: str
    CHROMA_PERSIST_DIRECTORY: str = "./chroma_data"
    
    # LLM/Embeddings
    HF_API_key: str
    gemini_api_key: str
    OPENROUTER_API_KEY: str | None = None
    
    # Neo4j
    NEO4J_URI: str
    NEO4J_USERNAME: str
    NEO4J_PASSWORD: str

    # Redis/Celery
    REDIS_URL: str

    # Genetic algorithm sizing (lower these for quick test runs)
    GA_GENERATIONS: int = 20
    GA_SEED_POPULATION: int = 10
    GA_POPULATION_SIZE: int = 20

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
