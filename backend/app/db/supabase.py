from supabase import create_client, Client
from app.core.config import settings

def get_supabase_client() -> Client:
    """Initialize and return the Supabase client as a singleton."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

supabase_client = get_supabase_client()
