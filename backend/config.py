"""
Supabase client and environment config.
Import `supabase` from here across all modules.
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL: str = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY: str = os.environ["SUPABASE_SERVICE_KEY"]  # service key for server-side ops

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
