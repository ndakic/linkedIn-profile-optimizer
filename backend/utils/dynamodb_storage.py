"""
DynamoDB storage utility for LinkedIn Profile Optimizer results.

This module handles storing and retrieving optimization results from DynamoDB.
"""

import json
import logging
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, Optional, List
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from botocore.config import Config as BotoConfig

from config import config

logger = logging.getLogger(__name__)


def convert_floats_to_decimal(obj: Any) -> Any:
    """
    Recursively convert all float values to Decimal for DynamoDB compatibility.

    Args:
        obj: Any Python object (dict, list, float, etc.)

    Returns:
        Same object structure with floats converted to Decimals
    """
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_floats_to_decimal(item) for item in obj)
    else:
        return obj


class DynamoDBStorage:
    """Utility class for storing and retrieving optimization results in DynamoDB."""

    def __init__(self):
        """Initialize DynamoDB client."""
        self.table_name = config.DYNAMODB_TABLE_NAME
        self.region = config.AWS_REGION

        # Configure boto3 with retry settings
        boto_config = BotoConfig(
            region_name=self.region,
            retries={
                'max_attempts': 3,
                'mode': 'adaptive'
            }
        )

        # Initialize DynamoDB client
        if config.AWS_ACCESS_KEY_ID and config.AWS_SECRET_ACCESS_KEY:
            self.dynamodb = boto3.resource(
                'dynamodb',
                aws_access_key_id=config.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
                config=boto_config
            )
            self.enabled = True
            logger.info(f"[DB] DynamoDB Storage initialized for table: {self.table_name}")
        else:
            self.dynamodb = None
            self.enabled = False
            logger.warning("[WARN] DynamoDB Storage disabled - AWS credentials not configured")

    def is_enabled(self) -> bool:
        """Check if DynamoDB storage is enabled."""
        return self.enabled

    def ensure_table_exists(self) -> bool:
        """
        Ensure the DynamoDB table exists, create if it doesn't.

        Returns:
            bool: True if table exists or was created successfully
        """
        if not self.enabled:
            return False

        try:
            table = self.dynamodb.Table(self.table_name)

            # Try to describe the table to check if it exists
            table.table_status
            logger.info(f"[OK] DynamoDB table '{self.table_name}' exists")
            return True

        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                # Table doesn't exist, create it
                logger.info(f"[CREATE] Creating DynamoDB table '{self.table_name}'...")
                return self._create_table()
            else:
                logger.error(f"[ERROR] Error checking table existence: {e}")
                return False
        except Exception as e:
            logger.error(f"[CRITICAL] Unexpected error checking table: {e}")
            return False

    def _create_table(self) -> bool:
        """
        Create the DynamoDB table with appropriate schema.

        Returns:
            bool: True if table was created successfully
        """
        try:
            table = self.dynamodb.create_table(
                TableName=self.table_name,
                KeySchema=[
                    {
                        'AttributeName': 'optimization_id',
                        'KeyType': 'HASH'  # Partition key
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'optimization_id',
                        'AttributeType': 'S'
                    }
                ],
                BillingMode='PAY_PER_REQUEST',  # On-demand billing
                Tags=[
                    {
                        'Key': 'Application',
                        'Value': 'LinkedIn-Profile-Optimizer'
                    },
                    {
                        'Key': 'Environment',
                        'Value': 'development' if config.DEBUG else 'production'
                    }
                ]
            )

            # Wait for the table to be created
            logger.info(f"[WAIT] Waiting for table '{self.table_name}' to be created...")
            table.wait_until_exists()

            logger.info(f"[OK] DynamoDB table '{self.table_name}' created successfully")
            return True

        except ClientError as e:
            logger.error(f"[ERROR] Failed to create table: {e}")
            return False
        except Exception as e:
            logger.error(f"[CRITICAL] Unexpected error creating table: {e}")
            return False

    async def save_step_progress(self, optimization_id: str, step_name: str,
                                step_data: Optional[Dict[str, Any]] = None,
                                status: str = "processing") -> bool:
        """
        Save individual step progress to DynamoDB.

        Args:
            optimization_id (str): Unique identifier for the optimization
            step_name (str): Name of the step (e.g., 'pdf_processing', 'profile_analysis')
            step_data (Optional[Dict[str, Any]]): Data specific to this step
            status (str): Overall status ('processing', 'completed', 'failed')

        Returns:
            bool: True if saved successfully
        """
        if not self.enabled:
            logger.warning(f"[WARN] Cannot save step progress - DynamoDB storage is disabled")
            return False

        start_time = time.time()
        logger.info(f"[WRITE] [ID:{optimization_id}] Saving step progress: {step_name}")

        try:
            table = self.dynamodb.Table(self.table_name)
            current_time = datetime.now(timezone.utc).isoformat()

            # Get existing item or create new one
            try:
                response = table.get_item(Key={'optimization_id': optimization_id})
                item = response.get('Item', {})
            except ClientError:
                item = {}

            # Initialize progress tracking fields if they don't exist
            if 'processing_steps' not in item:
                item['processing_steps'] = []
            if 'step_details' not in item:
                item['step_details'] = {}

            # Add completed step to list if not already there
            completed_steps = item.get('processing_steps', [])
            if step_name not in completed_steps:
                completed_steps.append(step_name)

            # Update step details (convert floats to Decimal)
            step_details = item.get('step_details', {})
            step_details[step_name] = {
                'completed_at': current_time,
                'data': convert_floats_to_decimal(step_data or {}),
                'duration': Decimal(str(step_data.get('duration', 0))) if step_data and 'duration' in step_data else Decimal('0')
            }

            # Update item (convert floats to Decimal)
            item.update({
                'optimization_id': optimization_id,
                'processing_steps': completed_steps,
                'current_step': step_name,
                'status': status,
                'step_details': step_details,
                'updated_at': current_time,
                'ttl': int(time.time()) + (30 * 24 * 60 * 60)  # 30 days TTL
            })

            # If this is the first step, also set created_at
            if 'created_at' not in item:
                item['created_at'] = current_time

            # Convert all floats in the entire item before saving
            item = convert_floats_to_decimal(item)

            table.put_item(Item=item)

            save_time = time.time() - start_time
            logger.info(f"[OK] [ID:{optimization_id}] Step progress saved in {save_time:.2f}s")
            return True

        except Exception as e:
            save_time = time.time() - start_time
            logger.error(f"[ERROR] [ID:{optimization_id}] Failed to save step progress after {save_time:.2f}s: {str(e)}")
            return False

    async def get_optimization_progress(self, optimization_id: str) -> Optional[Dict[str, Any]]:
        """
        Get optimization progress by ID.

        Args:
            optimization_id (str): Unique identifier for the optimization

        Returns:
            Optional[Dict[str, Any]]: Progress data or None if not found
        """
        if not self.enabled:
            logger.warning(f"[WARN] Cannot get progress - DynamoDB storage is disabled")
            return None

        start_time = time.time()
        logger.info(f"[INFO] [ID:{optimization_id}] Retrieving optimization progress...")

        try:
            table = self.dynamodb.Table(self.table_name)

            response = table.get_item(Key={'optimization_id': optimization_id})

            if 'Item' not in response:
                retrieve_time = time.time() - start_time
                logger.info(f"[INFO] [ID:{optimization_id}] Progress not found after {retrieve_time:.2f}s")
                return None

            item = response['Item']
            retrieve_time = time.time() - start_time
            logger.info(f"[OK] [ID:{optimization_id}] Progress retrieved in {retrieve_time:.2f}s")

            # Return progress-specific data
            return {
                'optimization_id': item.get('optimization_id'),
                'status': item.get('status', 'unknown'),
                'current_step': item.get('current_step'),
                'processing_steps': item.get('processing_steps', []),
                'step_details': item.get('step_details', {}),
                'created_at': item.get('created_at'),
                'updated_at': item.get('updated_at'),
                # Include results if available (for backwards compatibility)
                'results': json.loads(item.get('results', '{}')) if item.get('results') else None
            }

        except Exception as e:
            retrieve_time = time.time() - start_time
            logger.error(f"[ERROR] [ID:{optimization_id}] Failed to get progress after {retrieve_time:.2f}s: {str(e)}")
            return None

    async def save_optimization_result(self, optimization_id: str, results: Dict[str, Any],
                                     request_metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Save optimization results to DynamoDB.

        Args:
            optimization_id (str): Unique identifier for the optimization
            results (Dict[str, Any]): Optimization results to save
            request_metadata (Optional[Dict[str, Any]]): Additional metadata about the request

        Returns:
            bool: True if saved successfully
        """
        if not self.enabled:
            logger.warning(f"[WARN] Cannot save results - DynamoDB storage is disabled")
            return False

        start_time = time.time()
        logger.info(f"[SAVE] [ID:{optimization_id}] Saving optimization results to DynamoDB...")

        try:
            table = self.dynamodb.Table(self.table_name)

            # Prepare item for storage
            current_time = datetime.now(timezone.utc).isoformat()

            item = {
                'optimization_id': optimization_id,
                'results': json.dumps(results, default=str),  # Serialize complex objects
                'created_at': current_time,
                'updated_at': current_time,
                'status': 'completed' if results.get('success') else 'failed',
                'ttl': int(time.time()) + (30 * 24 * 60 * 60)  # 30 days TTL
            }

            # Add metadata if provided
            if request_metadata:
                item['metadata'] = json.dumps(request_metadata, default=str)

            # Add result summary for easy querying
            if results.get('success'):
                summary = results.get('summary', {})
                item['profile_score'] = summary.get('optimization_score', 0)
                item['completeness_score'] = summary.get('profile_completeness', 0)
                item['recommendations_count'] = len(summary.get('key_improvements', []))
                item['content_ideas_count'] = len(results.get('content_results', {}).get('content_ideas', []))

            # Convert all floats to Decimal before saving
            item = convert_floats_to_decimal(item)

            # Save to DynamoDB
            table.put_item(Item=item)

            save_time = time.time() - start_time
            logger.info(f"[OK] [ID:{optimization_id}] Results saved to DynamoDB in {save_time:.2f}s")
            return True

        except ClientError as e:
            save_time = time.time() - start_time
            logger.error(f"[ERROR] [ID:{optimization_id}] DynamoDB save failed after {save_time:.2f}s: {e}")
            return False
        except Exception as e:
            save_time = time.time() - start_time
            logger.error(f"[CRITICAL] [ID:{optimization_id}] Unexpected save error after {save_time:.2f}s: {e}")
            return False

    async def get_optimization_result(self, optimization_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve optimization results from DynamoDB.

        Args:
            optimization_id (str): Unique identifier for the optimization

        Returns:
            Optional[Dict[str, Any]]: Optimization results if found, None otherwise
        """
        if not self.enabled:
            logger.warning(f"[WARN] Cannot retrieve results - DynamoDB storage is disabled")
            return None

        start_time = time.time()
        logger.info(f"[INFO] [ID:{optimization_id}] Retrieving optimization results from DynamoDB...")

        try:
            table = self.dynamodb.Table(self.table_name)

            # Get item from DynamoDB
            response = table.get_item(
                Key={'optimization_id': optimization_id}
            )

            if 'Item' not in response:
                retrieve_time = time.time() - start_time
                logger.warning(f"[NOTFOUND] [ID:{optimization_id}] No results found after {retrieve_time:.2f}s")
                return None

            item = response['Item']

            # Parse the stored results
            results = json.loads(item['results'])

            # Add metadata about storage
            results['storage_info'] = {
                'optimization_id': optimization_id,
                'created_at': item.get('created_at'),
                'status': item.get('status'),
                'retrieved_at': datetime.now(timezone.utc).isoformat()
            }

            # Add metadata if available
            if 'metadata' in item:
                results['request_metadata'] = json.loads(item['metadata'])

            retrieve_time = time.time() - start_time
            logger.info(f"[OK] [ID:{optimization_id}] Results retrieved from DynamoDB in {retrieve_time:.2f}s")
            return results

        except ClientError as e:
            retrieve_time = time.time() - start_time
            logger.error(f"[ERROR] [ID:{optimization_id}] DynamoDB retrieval failed after {retrieve_time:.2f}s: {e}")
            return None
        except Exception as e:
            retrieve_time = time.time() - start_time
            logger.error(f"[CRITICAL] [ID:{optimization_id}] Unexpected retrieval error after {retrieve_time:.2f}s: {e}")
            return None

    async def list_recent_optimizations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List recent optimization results (requires GSI on created_at).

        Args:
            limit (int): Maximum number of results to return

        Returns:
            List[Dict[str, Any]]: List of recent optimization summaries
        """
        if not self.enabled:
            logger.warning("[WARN] Cannot list results - DynamoDB storage is disabled")
            return []

        try:
            table = self.dynamodb.Table(self.table_name)

            # Note: This is a simple scan - in production, you'd want a GSI on created_at
            response = table.scan(
                ProjectionExpression='optimization_id, created_at, #status, profile_score, completeness_score',
                ExpressionAttributeNames={'#status': 'status'},
                Limit=limit
            )

            items = response.get('Items', [])

            # Sort by created_at (newest first)
            items.sort(key=lambda x: x.get('created_at', ''), reverse=True)

            logger.info(f"[LIST] Retrieved {len(items)} recent optimization results")
            return items[:limit]

        except Exception as e:
            logger.error(f"[ERROR] Failed to list recent optimizations: {e}")
            return []

    async def delete_optimization_result(self, optimization_id: str) -> bool:
        """
        Delete optimization results from DynamoDB.

        Args:
            optimization_id (str): Unique identifier for the optimization

        Returns:
            bool: True if deleted successfully
        """
        if not self.enabled:
            logger.warning(f"[WARN] Cannot delete results - DynamoDB storage is disabled")
            return False

        try:
            table = self.dynamodb.Table(self.table_name)

            table.delete_item(
                Key={'optimization_id': optimization_id}
            )

            logger.info(f"[DELETE] [ID:{optimization_id}] Results deleted from DynamoDB")
            return True

        except Exception as e:
            logger.error(f"[ERROR] [ID:{optimization_id}] Failed to delete results: {e}")
            return False


# Global storage instance
storage = DynamoDBStorage()