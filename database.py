from supabase import create_client
import os
from dotenv import load_dotenv
load_dotenv()

#Supabase client setup
supabase_url = os.getenv("SUPABASE_API_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

if not supabase_url or not supabase_key:
    raise ValueError("Supabase URL or Service Key is not set in environment variables.")

supabase = create_client(supabase_url, supabase_key)