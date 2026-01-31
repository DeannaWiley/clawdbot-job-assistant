"""
Supabase Configuration for ClawdBot
====================================
Environment variable setup and configuration management.

Environment Variables Required:
- SUPABASE_URL: Your Supabase project URL (e.g., https://xxxxx.supabase.co)
- SUPABASE_ANON_KEY: Public anonymous key for client-side access
- SUPABASE_SERVICE_ROLE_KEY: (Optional) Service role key for elevated access

Usage:
    from supabase.config import get_supabase_client, get_service_client
    
    # Standard client (uses anon key, respects RLS)
    client = get_supabase_client()
    
    # Service client (bypasses RLS, use carefully)
    admin_client = get_service_client()
"""

import os
import sys
from typing import Optional
from dataclasses import dataclass
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class SupabaseConfig:
    """Supabase configuration container."""
    url: str
    anon_key: str
    service_role_key: Optional[str] = None
    
    @property
    def is_valid(self) -> bool:
        """Check if minimum configuration is present."""
        return bool(self.url and self.anon_key)
    
    @property
    def has_service_key(self) -> bool:
        """Check if service role key is available."""
        return bool(self.service_role_key)


def load_env_var(var_name: str, required: bool = True) -> Optional[str]:
    """
    Load environment variable from multiple sources.
    
    Priority:
    1. Current process environment
    2. Windows user environment variables
    3. .env file in project root
    
    Args:
        var_name: Name of the environment variable
        required: If True, raises error when not found
    
    Returns:
        The variable value or None
    """
    # Try current environment first
    value = os.environ.get(var_name)
    if value:
        return value
    
    # Try Windows user environment
    try:
        import subprocess
        result = subprocess.run(
            ['powershell', '-NoProfile', '-Command',
             f'[Environment]::GetEnvironmentVariable("{var_name}", "User")'],
            capture_output=True, text=True, timeout=5
        )
        value = result.stdout.strip()
        if value and value != 'None':
            os.environ[var_name] = value
            return value
    except Exception:
        pass
    
    # Try .env file
    env_paths = [
        Path(__file__).parent.parent / '.env',
        Path(__file__).parent.parent.parent / '.env',
        Path.home() / '.clawd' / '.env',
    ]
    
    for env_path in env_paths:
        if env_path.exists():
            try:
                with open(env_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith(f'{var_name}='):
                            value = line.split('=', 1)[1].strip().strip('"').strip("'")
                            if value:
                                os.environ[var_name] = value
                                return value
            except Exception:
                continue
    
    if required:
        raise EnvironmentError(
            f"Required environment variable '{var_name}' not found.\n"
            f"Please set it using one of:\n"
            f"  1. Set-Item -Path Env:{var_name} -Value 'your_value'\n"
            f"  2. [Environment]::SetEnvironmentVariable('{var_name}', 'your_value', 'User')\n"
            f"  3. Add to .env file: {var_name}=your_value"
        )
    
    return None


def get_config() -> SupabaseConfig:
    """
    Load Supabase configuration from environment.
    
    Returns:
        SupabaseConfig with loaded values
    
    Raises:
        EnvironmentError if required variables are missing
    """
    return SupabaseConfig(
        url=load_env_var('SUPABASE_URL', required=True),
        anon_key=load_env_var('SUPABASE_ANON_KEY', required=True),
        service_role_key=load_env_var('SUPABASE_SERVICE_ROLE_KEY', required=False)
    )


# Singleton clients
_anon_client = None
_service_client = None


def get_supabase_client():
    """
    Get Supabase client using anon key (respects RLS).
    
    This client should be used for:
    - Standard CRUD operations
    - User-scoped queries
    - Any operation that should respect Row Level Security
    
    Returns:
        Supabase client instance
    """
    global _anon_client
    
    if _anon_client is None:
        try:
            # Import using importlib to avoid conflicts with local module
            import importlib
            supabase_pkg = importlib.import_module('supabase._sync.client')
            create_client = supabase_pkg.create_client
        except (ImportError, AttributeError):
            try:
                # Try alternative import path
                import supabase as sb_pkg
                create_client = sb_pkg.create_client
            except ImportError:
                raise ImportError(
                    "supabase-py not installed. Run: pip install supabase"
                )
        
        config = get_config()
        _anon_client = create_client(config.url, config.anon_key)
        print(f"✅ Supabase client initialized (URL: {config.url[:30]}...)")
    
    return _anon_client


def get_service_client():
    """
    Get Supabase client using service role key (bypasses RLS).
    
    ⚠️ WARNING: This client bypasses Row Level Security!
    
    Use ONLY for:
    - Admin operations
    - Background jobs (cleanup, aggregation)
    - Analytics queries across all users
    - Data migrations
    
    Returns:
        Supabase client with elevated privileges
    
    Raises:
        EnvironmentError if service role key is not configured
    """
    global _service_client
    
    if _service_client is None:
        try:
            from supabase import create_client, Client
        except ImportError:
            raise ImportError(
                "supabase-py not installed. Run: pip install supabase"
            )
        
        config = get_config()
        
        if not config.has_service_key:
            raise EnvironmentError(
                "SUPABASE_SERVICE_ROLE_KEY not configured.\n"
                "This key is required for admin operations.\n"
                "Find it in: Supabase Dashboard > Settings > API > service_role key"
            )
        
        _service_client = create_client(config.url, config.service_role_key)
        print(f"⚠️ Supabase SERVICE client initialized (elevated privileges)")
    
    return _service_client


def test_connection() -> bool:
    """
    Test Supabase connection and configuration.
    
    Returns:
        True if connection successful
    """
    try:
        client = get_supabase_client()
        # Try a simple query
        result = client.table('users').select('id').limit(1).execute()
        print(f"✅ Supabase connection test passed")
        return True
    except Exception as e:
        print(f"❌ Supabase connection test failed: {e}")
        return False


# Environment variable documentation
ENV_VAR_DOCS = """
================================================================================
SUPABASE ENVIRONMENT VARIABLES
================================================================================

1. SUPABASE_URL
   - Your Supabase project URL
   - Format: https://xxxxx.supabase.co
   - Find it: Supabase Dashboard > Settings > API > Project URL
   - Example: https://abcdefghijklmnop.supabase.co

2. SUPABASE_ANON_KEY
   - Public anonymous key for client-side access
   - Safe to use in client code (with RLS enabled)
   - Find it: Supabase Dashboard > Settings > API > anon public
   - Example: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

3. SUPABASE_SERVICE_ROLE_KEY (Optional but recommended)
   - Service role key for server-side admin access
   - ⚠️ NEVER expose this key in client code!
   - Bypasses Row Level Security
   - Find it: Supabase Dashboard > Settings > API > service_role secret
   - Example: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

SETUP METHODS:
--------------

PowerShell (Session):
    $env:SUPABASE_URL = "https://xxxxx.supabase.co"
    $env:SUPABASE_ANON_KEY = "your_anon_key"
    $env:SUPABASE_SERVICE_ROLE_KEY = "your_service_key"

PowerShell (Permanent - User level):
    [Environment]::SetEnvironmentVariable("SUPABASE_URL", "https://xxxxx.supabase.co", "User")
    [Environment]::SetEnvironmentVariable("SUPABASE_ANON_KEY", "your_anon_key", "User")
    [Environment]::SetEnvironmentVariable("SUPABASE_SERVICE_ROLE_KEY", "your_service_key", "User")

.env file (in project root):
    SUPABASE_URL=https://xxxxx.supabase.co
    SUPABASE_ANON_KEY=your_anon_key
    SUPABASE_SERVICE_ROLE_KEY=your_service_key

================================================================================
"""


if __name__ == "__main__":
    print(ENV_VAR_DOCS)
    print("\nTesting configuration...")
    try:
        config = get_config()
        print(f"✅ URL: {config.url}")
        print(f"✅ Anon Key: {config.anon_key[:20]}...")
        if config.has_service_key:
            print(f"✅ Service Key: {config.service_role_key[:20]}...")
        else:
            print(f"⚠️ Service Key: Not configured (optional)")
        
        print("\nTesting connection...")
        test_connection()
    except Exception as e:
        print(f"❌ Configuration error: {e}")
