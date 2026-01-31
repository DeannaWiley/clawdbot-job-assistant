"""
Supabase Backend Integration for ClawdBot
==========================================

This package provides complete backend storage and tracking
for the ClawdBot job application automation system.

Quick Start:
    from supabase import get_db
    
    db = get_db()
    job_id = db.save_job(job_data)
    app_id = db.create_application(app_data)

Modules:
    - config: Environment configuration and client setup
    - client: High-level API for job tracking workflows
    - workflows: Complete workflow implementations
"""

from .config import (
    get_supabase_client,
    get_service_client,
    get_config,
    test_connection,
    SupabaseConfig,
)

from .client import (
    SupabaseClient,
    get_db,
    JobData,
    ApplicationData,
    DEFAULT_USER_ID,
)

__all__ = [
    # Config
    'get_supabase_client',
    'get_service_client', 
    'get_config',
    'test_connection',
    'SupabaseConfig',
    
    # Client
    'SupabaseClient',
    'get_db',
    'JobData',
    'ApplicationData',
    'DEFAULT_USER_ID',
]

__version__ = '1.0.0'
