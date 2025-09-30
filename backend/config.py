"""
Configuration module for LinkedIn Profile Optimizer.

This module handles loading and managing environment variables and application settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from .env file
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    load_dotenv(env_file)


class Config:
    """Application configuration class."""

    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")

    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # File Upload Configuration
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", str(10 * 1024 * 1024)))  # 10MB default
    ALLOWED_EXTENSIONS: list = [".pdf"]

    # LLM Configuration
    DEFAULT_TEMPERATURE: float = float(os.getenv("DEFAULT_TEMPERATURE", "0.3"))
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "4000"))

    # CORS Configuration
    ALLOWED_ORIGINS: list = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

    @classmethod
    def validate(cls) -> bool:
        """
        Validate that all required configuration is present.

        Returns:
            bool: True if configuration is valid, False otherwise
        """
        if not cls.OPENAI_API_KEY:
            print("❌ OPENAI_API_KEY is required but not set in environment variables")
            return False

        if not cls.OPENAI_API_KEY.startswith("sk-"):
            print("❌ OPENAI_API_KEY appears to be invalid (should start with 'sk-')")
            return False

        return True

    @classmethod
    def print_config(cls) -> None:
        """Print current configuration (excluding sensitive data)."""
        print("🔧 Current Configuration:")
        print(f"   OpenAI Model: {cls.OPENAI_MODEL}")
        print(f"   Host: {cls.HOST}")
        print(f"   Port: {cls.PORT}")
        print(f"   Debug Mode: {cls.DEBUG}")
        print(f"   Max File Size: {cls.MAX_FILE_SIZE / 1024 / 1024:.1f} MB")
        print(f"   Default Temperature: {cls.DEFAULT_TEMPERATURE}")
        print(f"   Max Tokens: {cls.MAX_TOKENS}")
        print(f"   Allowed Origins: {', '.join(cls.ALLOWED_ORIGINS)}")

        # Show API key status without revealing the key
        if cls.OPENAI_API_KEY:
            masked_key = cls.OPENAI_API_KEY[:8] + "..." + cls.OPENAI_API_KEY[-4:]
            print(f"   OpenAI API Key: {masked_key} ✓")
        else:
            print("   OpenAI API Key: Not set ❌")


# Global configuration instance
config = Config()


def get_openai_model() -> str:
    """Get the configured OpenAI model."""
    return config.OPENAI_MODEL


def get_openai_api_key() -> str:
    """Get the configured OpenAI API key."""
    return config.OPENAI_API_KEY


def is_debug_mode() -> bool:
    """Check if debug mode is enabled."""
    return config.DEBUG


def validate_config() -> bool:
    """Validate the current configuration."""
    return config.validate()
