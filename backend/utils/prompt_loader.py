import yaml
from typing import Dict, Any
from pathlib import Path


class PromptLoader:
    """Utility class for loading and managing prompts from YAML files."""

    def __init__(self, prompts_file: str = "prompts.yaml"):
        self.prompts_file = Path(__file__).parent.parent / prompts_file
        self.prompts = self._load_prompts()

    def _load_prompts(self) -> Dict[str, Any]:
        """Load prompts from YAML file."""
        try:
            with open(self.prompts_file, 'r', encoding='utf-8') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompts file not found: {self.prompts_file}")
        except yaml.YAMLError as e:
            raise Exception(f"Error parsing prompts YAML: {str(e)}")

    def get_system_prompt(self, agent_name: str) -> str:
        """Get system prompt for a specific agent."""
        try:
            return self.prompts[agent_name]["system_prompt"]
        except KeyError:
            raise KeyError(f"System prompt not found for agent: {agent_name}")

    def get_user_prompt(self, agent_name: str) -> str:
        """Get user prompt template for a specific agent."""
        try:
            return self.prompts[agent_name]["user_prompt"]
        except KeyError:
            raise KeyError(f"User prompt not found for agent: {agent_name}")

    def format_user_prompt(self, agent_name: str, **kwargs) -> str:
        """Format user prompt with provided parameters."""
        template = self.get_user_prompt(agent_name)
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise KeyError(f"Missing parameter for prompt formatting: {str(e)}")

    def get_all_prompts(self) -> Dict[str, Any]:
        """Get all loaded prompts."""
        return self.prompts

    def reload_prompts(self):
        """Reload prompts from file."""
        self.prompts = self._load_prompts()