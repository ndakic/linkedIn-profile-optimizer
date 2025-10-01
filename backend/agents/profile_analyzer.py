import json
import logging
import re
import time
from typing import Dict, Any, Optional, List
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from utils.prompt_loader import PromptLoader
from config import config

logger = logging.getLogger(__name__)


def extract_json_from_markdown(content: str) -> str:
    """
    Extract JSON from markdown code blocks.

    Handles cases where LLM returns JSON wrapped in ```json ... ``` blocks.

    Args:
        content: Raw LLM response that may contain markdown

    Returns:
        Clean JSON string
    """
    # Try to extract JSON from markdown code blocks
    json_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
    match = re.search(json_pattern, content)

    if match:
        return match.group(1).strip()

    # If no code block found, return original content (might be raw JSON)
    return content.strip()


class ProfileAnalyzerAgent:
    """Agent responsible for analyzing LinkedIn profile data and providing optimization recommendations."""

    def __init__(self, model_name: Optional[str] = None, api_key: Optional[str] = None):
        self.llm = ChatOpenAI(
            model=model_name or config.OPENAI_MODEL,
            temperature=1.0,
            # max_completion_tokens=config.MAX_TOKENS,
            openai_api_key=api_key or config.OPENAI_API_KEY
        )
        self.prompt_loader = PromptLoader()

    async def analyze_profile(self, profile_data: Dict[str, Any], target_role: Optional[str] = None, request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze LinkedIn profile data and provide optimization recommendations.

        Args:
            profile_data (Dict[str, Any]): Extracted profile data from ProfileCollectorAgent
            target_role (Optional[str]): Target industry/role for optimization
            request_id (Optional[str]): Request ID for tracking

        Returns:
            Dict[str, Any]: Analysis results with recommendations
        """
        req_id = request_id or "unknown"
        start_time = time.time()

        logger.info(f"[INFO] [REQ:{req_id}] Profile Analyzer - Starting analysis for target role: {target_role or 'General'}")

        try:
            # Validate input data
            if not profile_data:
                logger.error(f"[ERROR] [REQ:{req_id}] Empty profile data provided")
                raise ValueError("Profile data cannot be empty")

            # Get prompts for the agent
            system_prompt = self.prompt_loader.get_system_prompt("profile_analyzer")
            user_prompt = self.prompt_loader.format_user_prompt(
                "profile_analyzer",
                profile_data=json.dumps(profile_data, indent=2),
                target_role=target_role or "General professional development"
            )

            # Create messages for the LLM
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]

            # Get response from LLM
            logger.info(f"[LLM] [REQ:{req_id}] Sending analysis request to {config.OPENAI_MODEL}...")
            llm_start = time.time()
            response = await self.llm.ainvoke(messages)
            llm_time = time.time() - llm_start

            # Extract token usage from response
            token_usage = {
                'model': config.OPENAI_MODEL,
                'prompt_tokens': response.response_metadata.get('token_usage', {}).get('prompt_tokens', 0),
                'completion_tokens': response.response_metadata.get('token_usage', {}).get('completion_tokens', 0),
                'total_tokens': response.response_metadata.get('token_usage', {}).get('total_tokens', 0)
            }

            logger.info(f"[LLM] [REQ:{req_id}] Analysis response received in {llm_time:.2f}s")
            logger.info(f"[LLM] [REQ:{req_id}] Token usage - Prompt: {token_usage['prompt_tokens']}, Completion: {token_usage['completion_tokens']}, Total: {token_usage['total_tokens']}")

            # Parse JSON response
            try:
                # Extract JSON from markdown if wrapped in code blocks
                clean_json = extract_json_from_markdown(response.content)
                analysis_results = json.loads(clean_json)
                validated_results = self._validate_analysis_results(analysis_results)

                total_time = time.time() - start_time
                logger.info(f"[OK] [REQ:{req_id}] Profile analysis completed in {total_time:.2f}s")
                logger.info(f"[INFO] [REQ:{req_id}] Analysis score: {validated_results.get('overall_score', 'N/A')}/100")

                # Add token usage to results
                validated_results['token_usage'] = token_usage

                return validated_results
            except json.JSONDecodeError as e:
                logger.error(f"[ERROR] [REQ:{req_id}] JSON parsing failed: {str(e)}")
                raise ValueError(f"Invalid JSON response from LLM: {str(e)}")

        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"[CRITICAL] [REQ:{req_id}] Profile analysis failed after {total_time:.2f}s: {str(e)}")
            raise Exception(f"Error analyzing profile: {str(e)}")

    def _validate_analysis_results(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and clean the analysis results.

        Args:
            analysis_results (Dict[str, Any]): Raw analysis results from LLM

        Returns:
            Dict[str, Any]: Validated and cleaned analysis results
        """
        # Ensure required keys exist
        required_keys = [
            "overall_score", "strengths", "areas_for_improvement",
            "recommendations", "industry_insights", "next_steps"
        ]

        for key in required_keys:
            if key not in analysis_results:
                if key in ["strengths", "areas_for_improvement", "next_steps"]:
                    analysis_results[key] = []
                elif key == "overall_score":
                    analysis_results[key] = 0
                elif key == "recommendations":
                    analysis_results[key] = {}
                else:
                    analysis_results[key] = ""

        # Validate overall_score range
        if not isinstance(analysis_results["overall_score"], (int, float)):
            analysis_results["overall_score"] = 0
        else:
            analysis_results["overall_score"] = max(0, min(100, analysis_results["overall_score"]))

        # Ensure recommendations structure
        recommendations = analysis_results.get("recommendations", {})

        # Validate headline recommendation
        if "headline" not in recommendations:
            recommendations["headline"] = {
                "current": "",
                "suggested": "",
                "reasoning": ""
            }

        # Validate summary recommendation
        if "summary" not in recommendations:
            recommendations["summary"] = {
                "current": "",
                "suggested": "",
                "reasoning": ""
            }

        # Validate experience optimization
        if "experience_optimization" not in recommendations:
            recommendations["experience_optimization"] = []
        elif not isinstance(recommendations["experience_optimization"], list):
            recommendations["experience_optimization"] = []

        # Validate skills recommendations
        for skill_key in ["skills_to_add", "skills_to_emphasize", "keywords_to_include", "certifications_to_pursue"]:
            if skill_key not in recommendations:
                recommendations[skill_key] = []
            elif not isinstance(recommendations[skill_key], list):
                recommendations[skill_key] = []

        analysis_results["recommendations"] = recommendations

        return analysis_results

    def generate_keyword_suggestions(self, profile_data: Dict[str, Any], target_industry: str) -> List[str]:
        """
        Generate industry-specific keyword suggestions.

        Args:
            profile_data (Dict[str, Any]): Profile data
            target_industry (str): Target industry

        Returns:
            List[str]: List of recommended keywords
        """
        # This could be enhanced with industry-specific keyword databases
        # For now, we'll rely on the LLM analysis
        return []

    def calculate_profile_completeness(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate profile completeness score based on filled sections.

        Args:
            profile_data (Dict[str, Any]): Profile data

        Returns:
            Dict[str, Any]: Completeness analysis
        """
        completeness_score = 0
        max_score = 100
        sections = {
            "personal_info": 20,
            "summary": 15,
            "experience": 20,
            "education": 10,
            "skills": 10,
            "certifications": 5,
            "recommendations": 10,
            "languages": 5,
            "volunteer_experience": 3,
            "publications_projects": 2
        }

        completed_sections = []
        missing_sections = []

        for section, weight in sections.items():
            data = profile_data.get(section)
            is_complete = False

            if section == "personal_info":
                # Check if critical personal info fields are filled
                if data and isinstance(data, dict):
                    critical_fields = ["name", "title"]
                    is_complete = all(data.get(field) for field in critical_fields)
            elif section == "summary":
                is_complete = bool(data and data.strip())
            else:
                # For list-based sections
                is_complete = bool(data and len(data) > 0)

            if is_complete:
                completeness_score += weight
                completed_sections.append(section)
            else:
                missing_sections.append(section)

        return {
            "completeness_score": completeness_score,
            "completed_sections": completed_sections,
            "missing_sections": missing_sections,
            "recommendations": [
                f"Complete the {section} section to improve your profile"
                for section in missing_sections
            ]
        }