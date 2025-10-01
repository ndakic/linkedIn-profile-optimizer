import json
import logging
import re
import time
from typing import Dict, Any, List, Optional
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


class ContentGeneratorAgent:
    """Agent responsible for generating LinkedIn content ideas and posts based on profile analysis."""

    def __init__(self, model_name: Optional[str] = None, api_key: Optional[str] = None):
        self.llm = ChatOpenAI(
            model=model_name or config.OPENAI_MODEL,
            temperature=1.0,
            # max_completion_tokens=config.MAX_TOKENS,
            openai_api_key=api_key or config.OPENAI_API_KEY
        )
        self.prompt_loader = PromptLoader()

    async def generate_content(self, profile_data: Dict[str, Any], profile_analysis: Dict[str, Any], request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate LinkedIn content ideas and posts based on profile analysis.

        Args:
            profile_data (Dict[str, Any]): Original profile data
            profile_analysis (Dict[str, Any]): Analysis results from ProfileAnalyzerAgent
            request_id (Optional[str]): Request ID for tracking

        Returns:
            Dict[str, Any]: Generated content strategy and sample posts
        """
        req_id = request_id or "unknown"
        start_time = time.time()

        logger.info(f"[INFO] [REQ:{req_id}] Content Generator - Starting content generation...")

        try:
            # Validate input data
            if not profile_data:
                logger.error(f"[ERROR] [REQ:{req_id}] Empty profile data provided")
                raise ValueError("Profile data cannot be empty")
            if not profile_analysis:
                logger.error(f"[ERROR] [REQ:{req_id}] Empty profile analysis provided")
                raise ValueError("Profile analysis cannot be empty")

            # Get prompts for the agent
            system_prompt = self.prompt_loader.get_system_prompt("content_generator")
            user_prompt = self.prompt_loader.format_user_prompt(
                "content_generator",
                profile_data=json.dumps(profile_data, indent=2),
                profile_analysis=json.dumps(profile_analysis, indent=2)
            )

            # Create messages for the LLM
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]

            # Get response from LLM
            logger.info(f"[LLM] [REQ:{req_id}] Sending content generation request to {config.OPENAI_MODEL}...")
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

            logger.info(f"[LLM] [REQ:{req_id}] Content generation response received in {llm_time:.2f}s")
            logger.info(f"[LLM] [REQ:{req_id}] Token usage - Prompt: {token_usage['prompt_tokens']}, Completion: {token_usage['completion_tokens']}, Total: {token_usage['total_tokens']}")

            # Parse JSON response
            try:
                # Extract JSON from markdown if wrapped in code blocks
                clean_json = extract_json_from_markdown(response.content)
                content_results = json.loads(clean_json)
                validated_results = self._validate_content_results(content_results)

                total_time = time.time() - start_time
                content_count = len(validated_results.get('content_ideas', []))
                posts_count = len(validated_results.get('sample_posts', []))

                logger.info(f"[OK] [REQ:{req_id}] Content generation completed in {total_time:.2f}s")
                logger.info(f"[INFO] [REQ:{req_id}] Generated {content_count} content ideas and {posts_count} sample posts")

                # Add token usage to results
                validated_results['token_usage'] = token_usage

                return validated_results
            except json.JSONDecodeError as e:
                logger.error(f"[ERROR] [REQ:{req_id}] JSON parsing failed: {str(e)}")
                raise ValueError(f"Invalid JSON response from LLM: {str(e)}")

        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"[CRITICAL] [REQ:{req_id}] Content generation failed after {total_time:.2f}s: {str(e)}")
            raise Exception(f"Error generating content: {str(e)}")

    def _validate_content_results(self, content_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and clean the content generation results.

        Args:
            content_results (Dict[str, Any]): Raw content results from LLM

        Returns:
            Dict[str, Any]: Validated and cleaned content results
        """
        # Ensure required keys exist
        required_keys = [
            "content_strategy", "content_ideas", "sample_posts", "weekly_content_calendar"
        ]

        for key in required_keys:
            if key not in content_results:
                content_results[key] = [] if key != "content_strategy" else {}

        # Validate content_strategy structure
        strategy = content_results.get("content_strategy", {})
        strategy_keys = ["posting_frequency", "best_posting_times", "content_pillars", "hashtag_strategy"]

        for key in strategy_keys:
            if key not in strategy:
                if key in ["best_posting_times", "content_pillars", "hashtag_strategy"]:
                    strategy[key] = []
                else:
                    strategy[key] = ""

        content_results["content_strategy"] = strategy

        # Validate content_ideas structure
        if not isinstance(content_results["content_ideas"], list):
            content_results["content_ideas"] = []

        for idea in content_results["content_ideas"]:
            required_idea_keys = ["type", "topic", "objective", "target_audience", "content", "hashtags", "call_to_action"]
            for key in required_idea_keys:
                if key not in idea:
                    if key == "hashtags":
                        idea[key] = []
                    else:
                        idea[key] = ""

        # Validate sample_posts structure
        if not isinstance(content_results["sample_posts"], list):
            content_results["sample_posts"] = []

        for post in content_results["sample_posts"]:
            required_post_keys = ["title", "content", "hashtags", "engagement_hooks"]
            for key in required_post_keys:
                if key not in post:
                    if key in ["hashtags", "engagement_hooks"]:
                        post[key] = []
                    else:
                        post[key] = ""

        # Validate weekly_content_calendar structure
        if not isinstance(content_results["weekly_content_calendar"], list):
            content_results["weekly_content_calendar"] = []

        for calendar_item in content_results["weekly_content_calendar"]:
            required_calendar_keys = ["day", "content_type", "topic", "brief_description"]
            for key in required_calendar_keys:
                if key not in calendar_item:
                    calendar_item[key] = ""

        return content_results

    async def generate_specific_post(self, topic: str, post_type: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a specific LinkedIn post for a given topic and type.

        Args:
            topic (str): Topic for the post
            post_type (str): Type of post (thought_leadership, achievement, industry_insight, etc.)
            profile_data (Dict[str, Any]): Profile data for context

        Returns:
            Dict[str, Any]: Generated post content
        """
        try:
            # Create a custom prompt for specific post generation
            custom_prompt = f"""
            Based on the following LinkedIn profile data, generate a {post_type} post about {topic}.

            Profile Data:
            {json.dumps(profile_data, indent=2)}

            The post should be:
            - Professional yet engaging
            - Authentic to the person's background
            - Optimized for LinkedIn engagement
            - Include relevant hashtags
            - Have a clear call-to-action

            Return the result as JSON with the following structure:
            {{
                "title": "string",
                "content": "string",
                "hashtags": ["string"],
                "engagement_hooks": ["string"],
                "best_posting_time": "string",
                "expected_engagement": "string"
            }}
            """

            # Get system prompt
            system_prompt = self.prompt_loader.get_system_prompt("content_generator")

            # Create messages for the LLM
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=custom_prompt)
            ]

            # Get response from LLM
            response = await self.llm.ainvoke(messages)

            # Parse JSON response
            try:
                # Extract JSON from markdown if wrapped in code blocks
                clean_json = extract_json_from_markdown(response.content)
                post_data = json.loads(clean_json)
                return self._validate_single_post(post_data)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON response from LLM: {str(e)}")

        except Exception as e:
            raise Exception(f"Error generating specific post: {str(e)}")

    def _validate_single_post(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a single post data structure.

        Args:
            post_data (Dict[str, Any]): Raw post data from LLM

        Returns:
            Dict[str, Any]: Validated post data
        """
        required_keys = ["title", "content", "hashtags", "engagement_hooks", "best_posting_time", "expected_engagement"]

        for key in required_keys:
            if key not in post_data:
                if key in ["hashtags", "engagement_hooks"]:
                    post_data[key] = []
                else:
                    post_data[key] = ""

        return post_data

    def get_content_categories(self) -> List[str]:
        """
        Get available content categories for LinkedIn posts.

        Returns:
            List[str]: List of content categories
        """
        return [
            "thought_leadership",
            "industry_insights",
            "career_achievements",
            "professional_tips",
            "team_appreciation",
            "project_showcase",
            "learning_journey",
            "networking_engagement",
            "company_culture",
            "industry_trends",
            "skill_development",
            "motivational_content"
        ]

    def get_post_types(self) -> List[str]:
        """
        Get available post types for LinkedIn content.

        Returns:
            List[str]: List of post types
        """
        return [
            "text_post",
            "image_post",
            "document_carousel",
            "video_post",
            "poll",
            "article",
            "event_announcement",
            "job_posting"
        ]