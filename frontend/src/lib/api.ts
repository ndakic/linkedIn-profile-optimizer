import { OptimizationResults } from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public details?: any
  ) {
    super(message);
    this.name = 'APIError';
  }
}

export async function optimizeProfile(
  file: File,
  targetRole?: string,
  optimizationId?: string,
  apiKey?: string
): Promise<OptimizationResults> {
  const formData = new FormData();
  formData.append('file', file);

  if (targetRole?.trim()) {
    formData.append('target_role', targetRole.trim());
  }

  if (optimizationId) {
    formData.append('optimization_id', optimizationId);
  }

  if (apiKey?.trim()) {
    formData.append('api_key', apiKey.trim());
  }

  try {
    const response = await fetch(`${API_BASE_URL}/optimize-profile`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new APIError(
        errorData.detail || `HTTP ${response.status}: ${response.statusText}`,
        response.status,
        errorData
      );
    }

    const data = await response.json();
    return data as OptimizationResults;
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }

    // Network or other errors
    throw new APIError(
      'Failed to connect to the server. Please try again.',
      0,
      { originalError: error }
    );
  }
}

export async function checkServerHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      method: 'GET',
    });
    return response.ok;
  } catch {
    return false;
  }
}