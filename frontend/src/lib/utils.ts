/**
 * Utility functions for the LinkedIn Profile Optimizer frontend
 */

/**
 * Generate a unique optimization ID (UUID v4 format)
 * @returns string - 36 character UUID
 */
export function generateOptimizationId(): string {
  // Generate a UUID v4 format: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

/**
 * Format file size in human readable format
 * @param bytes - File size in bytes
 * @returns string - Formatted file size
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Check if a string is a valid optimization ID format
 * @param id - ID to validate
 * @returns boolean - True if valid format
 */
export function isValidOptimizationId(id: string): boolean {
  // Should be 36-character UUID format or 6-50 characters alphanumeric
  const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  const shortPattern = /^[a-zA-Z0-9_-]{6,50}$/;
  return uuidPattern.test(id) || shortPattern.test(id);
}

/**
 * Check if an error is related to API key issues
 * @param errorMessage - Error message or response to check
 * @param errorData - Optional error data object
 * @returns boolean - True if error is API key related
 */
export function isApiKeyError(errorMessage: string, errorData?: any): boolean {
  if (!errorMessage && !errorData) return false;

  const message = (errorMessage || '').toLowerCase();

  // Check error message for API key related keywords
  const apiKeyKeywords = [
    'api key',
    'api_key',
    'apikey',
    'authentication',
    'unauthorized',
    'invalid_api_key',
    'invalid_request_error',
    'incorrect api key',
    'invalid api key',
    'authentication failed',
    'authenticationerror',
    'error code: 401',
    'error code: 403',
    '401 -',
    'platform.openai.com/account/api-keys'
  ];

  // Check if any keyword is present in the error message
  const hasKeyword = apiKeyKeywords.some(keyword => message.includes(keyword));

  // Check HTTP status codes related to authentication
  const isAuthError = errorData?.status === 401 ||
                     errorData?.status === 403 ||
                     errorData?.status_code === 401 ||
                     errorData?.status_code === 403;

  // Check error type/code in error data
  const hasAuthErrorType = errorData?.type === 'invalid_request_error' ||
                          errorData?.code === 'invalid_api_key' ||
                          errorData?.error?.code === 'invalid_api_key' ||
                          errorData?.error?.type === 'invalid_request_error';

  return hasKeyword || isAuthError || hasAuthErrorType;
}