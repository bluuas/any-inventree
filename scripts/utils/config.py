"""
Centralized configuration management for InvenTree operations.
Single source of truth for environment variables.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
import logging

logger = logging.getLogger('InvenTreeCLI')

# Find and load the top-level .env file
def _load_env_file():
    """Load environment variables from the top-level .env file."""
    # Get the current file's directory
    current_dir = Path(__file__).parent
    # Go up to find the project root (look for .env file)
    project_root = current_dir
    while project_root.parent != project_root:  # Stop at filesystem root
        env_file = project_root / '.env'
        if env_file.exists():
            load_dotenv(env_file)
            logger.debug(f"Loaded environment variables from: {env_file}")
            return project_root
        project_root = project_root.parent
    
    # If not found, try current directory and parent
    for path in [current_dir, current_dir.parent, current_dir.parent.parent]:
        env_file = path / '.env'
        if env_file.exists():
            load_dotenv(env_file)
            logger.debug(f"Loaded environment variables from: {env_file}")
            return path
    
    logger.warning("No .env file found in project tree")
    return None

# Load environment variables at module import
_project_root = _load_env_file()

class Config:
    """Configuration class with all environment variables."""
    
    # InvenTree API Configuration
    INVENTREE_API_URL = os.getenv("INVENTREE_API_URL", "http://inventree.localhost/api")
    INVENTREE_ADMIN_USER = os.getenv("INVENTREE_ADMIN_USER")
    INVENTREE_ADMIN_PASSWORD = os.getenv("INVENTREE_ADMIN_PASSWORD")
    INVENTREE_SITE_URL = os.getenv("INVENTREE_SITE_URL", "http://inventree.localhost")
    
    # Database Configuration
    DATABASE_HOST = os.getenv("DATABASE_HOST", "localhost")
    DATABASE_PORT = os.getenv("DATABASE_PORT", "5432")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "inventree")
    DATABASE_USER = os.getenv("DATABASE_USER", "inventree")
    DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
    
    # Application Configuration
    DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # KiCad Plugin Configuration
    KICAD_PLUGIN_PK = os.getenv("KICAD_PLUGIN_PK", "kicad-library-plugin")
    
    @classmethod
    def validate_required(cls):
        """
        Validate that all required environment variables are set.
        Returns list of missing variables.
        """
        required_vars = [
            ('INVENTREE_API_URL', cls.INVENTREE_API_URL),
            ('INVENTREE_ADMIN_USER', cls.INVENTREE_ADMIN_USER),
            ('INVENTREE_ADMIN_PASSWORD', cls.INVENTREE_ADMIN_PASSWORD),
        ]
        
        missing = []
        for var_name, var_value in required_vars:
            if not var_value:
                missing.append(var_name)
        
        return missing
    
    @classmethod
    def get_site_url(cls):
        """Get the InvenTree site URL for part links."""
        return cls.INVENTREE_SITE_URL
    
    @classmethod
    def get_api_credentials(cls):
        """Get API credentials as a dictionary."""
        return {
            'url': cls.INVENTREE_API_URL,
            'username': cls.INVENTREE_ADMIN_USER,
            'password': cls.INVENTREE_ADMIN_PASSWORD
        }
    
    @classmethod
    def print_config(cls):
        """Print current configuration (hiding sensitive values)."""
        print("=== InvenTree Configuration ===")
        print(f"API URL: {cls.INVENTREE_API_URL}")
        print(f"Site URL: {cls.INVENTREE_SITE_URL}")
        print(f"Username: {cls.INVENTREE_ADMIN_USER}")
        print(f"Password: {'*' * len(cls.INVENTREE_ADMIN_PASSWORD) if cls.INVENTREE_ADMIN_PASSWORD else 'Not set'}")
        print(f"Debug: {cls.DEBUG}")
        print(f"Log Level: {cls.LOG_LEVEL}")
        print("=" * 30)

# Convenience function to get site URL
def get_site_url():
    """Convenience function to get site URL."""
    return Config.get_site_url()

# Convenience function to get API credentials
def get_api_credentials():
    """Convenience function to get API credentials."""
    return Config.get_api_credentials()