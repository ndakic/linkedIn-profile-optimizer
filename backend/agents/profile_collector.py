import json
import logging
import re
import time
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from utils.pdf_parser import PDFParser
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


class ProfileCollectorAgent:
    """Agent responsible for extracting LinkedIn profile information from PDF files."""

    def __init__(self, model_name: Optional[str] = None, api_key: Optional[str] = None):
        self.llm = ChatOpenAI(
            model=model_name or config.OPENAI_MODEL,
            temperature=1.0,
            # max_completion_tokens=config.MAX_TOKENS,
            openai_api_key=api_key or config.OPENAI_API_KEY
        )
        self.pdf_parser = PDFParser()
        self.prompt_loader = PromptLoader()

    async def extract_profile_data(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract LinkedIn profile data from PDF file.

        Args:
            pdf_path (str): Path to the LinkedIn profile PDF

        Returns:
            Dict[str, Any]: Extracted profile data in structured format
        """
        try:
            # Validate PDF file
            if not self.pdf_parser.validate_pdf(pdf_path):
                raise ValueError("Invalid PDF file")

            # Extract text content from PDF
            pdf_content = self.pdf_parser.extract_text_from_pdf(pdf_path)

            if not pdf_content.strip():
                raise ValueError("No text content found in PDF")

            # Get prompts for the agent
            system_prompt = self.prompt_loader.get_system_prompt("profile_collector")
            user_prompt = self.prompt_loader.format_user_prompt(
                "profile_collector",
                pdf_content=pdf_content
            )

            # Create messages for the LLM
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]

            # Get response from LLM
            response = await self.llm.ainvoke(messages)

            # Parse JSON response
            try:
                # Extract JSON from markdown if wrapped in code blocks
                clean_json = extract_json_from_markdown(response.content)
                profile_data = json.loads(clean_json)
                return self._validate_profile_data(profile_data)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing failed: {str(e)}")
                logger.error(f"LLM response content: {response.content[:500]}...")
                raise ValueError(f"Invalid JSON response from LLM: {str(e)}")

        except Exception as e:
            raise Exception(f"Error extracting profile data: {str(e)}")

    async def extract_profile_data_from_bytes(self, pdf_bytes: bytes, request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract LinkedIn profile data from PDF bytes.

        Args:
            pdf_bytes (bytes): PDF content as bytes
            request_id (Optional[str]): Request ID for tracking

        Returns:
            Dict[str, Any]: Extracted profile data in structured format
        """
        req_id = request_id or "unknown"
        step_start = time.time()

        logger.info(f"[INFO] [REQ:{req_id}] Profile Collector - Starting PDF text extraction...")

        try:
            # Extract text content from PDF bytes
            extraction_start = time.time()
            pdf_content = self.pdf_parser.extract_text_from_bytes(pdf_bytes, req_id)
            extraction_time = time.time() - extraction_start

            logger.info(f"[INFO] [REQ:{req_id}] PDF text extracted in {extraction_time:.2f}s ({len(pdf_content)} characters)")

            if not pdf_content.strip():
                logger.error(f"[ERROR] [REQ:{req_id}] No text content found in PDF")
                raise ValueError("No text content found in PDF")

            # Get prompts for the agent
            logger.info(f"[INFO] [REQ:{req_id}] Loading system and user prompts...")
            system_prompt = self.prompt_loader.get_system_prompt("profile_collector")
            user_prompt = self.prompt_loader.format_user_prompt(
                "profile_collector",
                pdf_content=pdf_content
            )

            # Create messages for the LLM
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]

            logger.info(f"[LLM] [REQ:{req_id}] Sending profile data to {config.OPENAI_MODEL} for extraction...")
            llm_start = time.time()

            # Get response from LLM
            response = await self.llm.ainvoke(messages)
            llm_time = time.time() - llm_start

            # Extract token usage from response
            token_usage = {
                'model': config.OPENAI_MODEL,
                'prompt_tokens': response.response_metadata.get('token_usage', {}).get('prompt_tokens', 0),
                'completion_tokens': response.response_metadata.get('token_usage', {}).get('completion_tokens', 0),
                'total_tokens': response.response_metadata.get('token_usage', {}).get('total_tokens', 0)
            }

            logger.info(f"[LLM] [REQ:{req_id}] LLM response received in {llm_time:.2f}s ({len(response.content)} characters)")
            logger.info(f"[LLM] [REQ:{req_id}] Token usage - Prompt: {token_usage['prompt_tokens']}, Completion: {token_usage['completion_tokens']}, Total: {token_usage['total_tokens']}")

            # Parse JSON response
            try:
                parsing_start = time.time()

                # Extract JSON from markdown if wrapped in code blocks
                clean_json = extract_json_from_markdown(response.content)
                profile_data = json.loads(clean_json)
                parsing_time = time.time() - parsing_start

                logger.info(f"[INFO] [REQ:{req_id}] JSON parsing completed in {parsing_time:.2f}s")

                # Validate and clean data
                validation_start = time.time()
                validated_data = self._validate_profile_data(profile_data, req_id)
                validation_time = time.time() - validation_start

                total_time = time.time() - step_start
                logger.info(f"[OK] [REQ:{req_id}] Profile collection completed in {total_time:.2f}s")
                logger.info(f"[INFO] [REQ:{req_id}] Breakdown: PDF({extraction_time:.1f}s) + LLM({llm_time:.1f}s) + Parse({parsing_time:.1f}s) + Validate({validation_time:.1f}s)")

                # Add token usage to results
                validated_data['token_usage'] = token_usage

                return validated_data

            except json.JSONDecodeError as e:
                logger.error(f"[ERROR] [REQ:{req_id}] JSON parsing failed: {str(e)}")
                logger.error(f"[ERROR] [REQ:{req_id}] LLM response content: {response.content[:500]}...")
                raise ValueError(f"Invalid JSON response from LLM: {str(e)}")

        except Exception as e:
            total_time = time.time() - step_start
            logger.error(f"[CRITICAL] [REQ:{req_id}] Profile collection failed after {total_time:.2f}s: {str(e)}")
            raise Exception(f"Error extracting profile data from bytes: {str(e)}")

    def _validate_profile_data(self, profile_data: Dict[str, Any], request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate and clean the extracted profile data.

        Args:
            profile_data (Dict[str, Any]): Raw profile data from LLM
            request_id (Optional[str]): Request ID for tracking

        Returns:
            Dict[str, Any]: Validated and cleaned profile data
        """
        req_id = request_id or "unknown"
        logger.info(f"[INFO] [REQ:{req_id}] Validating extracted profile data...")
        required_keys = [
            "personal_info", "summary", "experience", "education",
            "skills", "certifications", "recommendations", "endorsements",
            "languages", "volunteer_experience", "publications_projects"
        ]

        # Ensure all required keys exist
        for key in required_keys:
            if key not in profile_data:
                profile_data[key] = [] if key != "summary" and key != "personal_info" else None

        # Validate personal_info structure
        if not profile_data.get("personal_info"):
            profile_data["personal_info"] = {}

        personal_info_keys = ["name", "title", "location", "email", "phone", "linkedin_url"]
        for key in personal_info_keys:
            if key not in profile_data["personal_info"]:
                profile_data["personal_info"][key] = None

        # Ensure lists are actually lists
        list_keys = ["experience", "education", "skills", "certifications",
                    "recommendations", "endorsements", "languages",
                    "volunteer_experience", "publications_projects"]

        for key in list_keys:
            if not isinstance(profile_data[key], list):
                profile_data[key] = []

        # Log validation results
        filled_sections = sum(1 for key in required_keys if profile_data.get(key))
        logger.info(f"[OK] [REQ:{req_id}] Profile validation completed: {filled_sections}/{len(required_keys)} sections filled")

        return profile_data

    def get_pdf_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """Get metadata from PDF file."""
        return self.pdf_parser.get_pdf_metadata(pdf_path)