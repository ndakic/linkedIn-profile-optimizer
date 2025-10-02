'use client';

import React, { useState, useCallback } from 'react';
import { UploadState } from '@/types';

interface FileUploadProps {
  onFileSelect: (file: File) => void;
  targetRole: string;
  onTargetRoleChange: (role: string) => void;
  apiKey: string;
  onApiKeyChange: (apiKey: string) => void;
  onOptimize: () => void;
  uploadState: UploadState;
  disabled?: boolean;
}

export default function FileUpload({
  onFileSelect,
  targetRole,
  onTargetRoleChange,
  apiKey,
  onApiKeyChange,
  onOptimize,
  uploadState,
  disabled = false,
}: FileUploadProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [fileError, setFileError] = useState<string>('');
  const [apiKeyError, setApiKeyError] = useState<string>('');
  const [showApiKey, setShowApiKey] = useState(false);

  const validateFile = (file: File): string | null => {
    // Check file type
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      return 'Only PDF files are allowed';
    }

    // Check file size (10MB limit)
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
      return 'File size exceeds 10MB limit';
    }

    return null;
  };

  const validateApiKey = (key: string): string | null => {
    // Check if API key is empty
    if (!key.trim()) {
      return 'Please provide your OpenAI API key';
    }

    // Check if API key starts with 'sk-'
    if (!key.startsWith('sk-')) {
      return "Invalid API key format. OpenAI API keys should start with 'sk-'";
    }

    // Check minimum length
    if (key.length < 20) {
      return 'Invalid API key. The key appears to be too short (minimum 20 characters)';
    }

    return null;
  };

  const handleFileSelect = useCallback((file: File) => {
    const error = validateFile(file);
    if (error) {
      setFileError(error);
      return;
    }

    setFileError('');
    setSelectedFile(file);
    onFileSelect(file);
  }, [onFileSelect]);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  }, [handleFileSelect]);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0]);
    }
  }, [handleFileSelect]);

  const handleTargetRoleChange = useCallback((value: string) => {
    onTargetRoleChange(value);
  }, [onTargetRoleChange]);

  const handleApiKeyChange = useCallback((value: string) => {
    onApiKeyChange(value);
    // Clear error when user modifies the API key
    if (apiKeyError) {
      setApiKeyError('');
    }
  }, [onApiKeyChange, apiKeyError]);

  const handleOptimizeClick = useCallback(() => {
    // Validate API key before proceeding
    const error = validateApiKey(apiKey);
    if (error) {
      setApiKeyError(error);
      return;
    }

    // Validate file
    if (!selectedFile) {
      return;
    }

    // Clear any errors and proceed
    setApiKeyError('');
    onOptimize();
  }, [apiKey, selectedFile, onOptimize]);

  const isOptimizeDisabled = !selectedFile || !apiKey.trim() || uploadState.isUploading || disabled;

  return (
    <div className="w-full max-w-2xl mx-auto">
      {/* File Upload Area */}
      <div
        className={`relative border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          dragActive
            ? 'border-linkedin bg-blue-50 dark:bg-blue-900/20'
            : fileError
            ? 'border-red-300 bg-red-50'
            : 'border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600'
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          type="file"
          accept=".pdf"
          onChange={handleInputChange}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer pointer-events-auto"
          style={{ pointerEvents: disabled ? 'none' : 'auto' }}
          disabled={disabled}
        />

        <div className="space-y-4">
          <div className="text-4xl">📄</div>

          {selectedFile ? (
            <div className="space-y-2">
              <p className="text-green-600 dark:text-green-400 font-medium">
                ✅ {selectedFile.name}
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Size: {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              <p className="text-lg font-medium text-gray-700 dark:text-white">
                Upload your LinkedIn profile PDF
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Drag and drop your file here, or click to select
              </p>
            </div>
          )}

          {fileError && (
            <p className="text-red-600 dark:text-red-400 text-sm font-medium">
              ❌ {fileError}
            </p>
          )}

          <p className="text-xs text-gray-400 dark:text-gray-500">
            Maximum file size: 10MB • PDF format only
          </p>
        </div>
      </div>

      {/* OpenAI API Key Input */}
      <div className="mt-6 space-y-2 relative z-10">
        <label htmlFor="apiKey" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          OpenAI API Key <span className="text-red-500">*</span>
        </label>
        <div className="relative">
          <input
            id="apiKey"
            type={showApiKey ? "text" : "password"}
            value={apiKey}
            onChange={(e) => handleApiKeyChange(e.target.value)}
            placeholder="sk-proj-..."
            className={`w-full px-4 py-2 pr-12 border rounded-lg focus:ring-2 focus:ring-linkedin focus:border-transparent relative z-10 text-gray-900 dark:text-white bg-white dark:bg-gray-700 font-mono text-sm ${
              apiKeyError ? 'border-red-300' : 'border-gray-300 dark:border-gray-600'
            }`}
            disabled={disabled}
            autoComplete="off"
            required
          />
          <button
            type="button"
            onClick={() => setShowApiKey(!showApiKey)}
            className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
            tabIndex={-1}
          >
            {showApiKey ? '👁️' : '👁️‍🗨️'}
          </button>
        </div>
        {apiKeyError && (
          <p className="text-red-600 dark:text-red-400 text-sm font-medium">
            ❌ {apiKeyError}
          </p>
        )}
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Your API key is only used for this request and never stored. Get yours at{' '}
          <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className="text-linkedin hover:underline">
            platform.openai.com/api-keys
          </a>
        </p>
      </div>

      {/* Target Role Input */}
      <div className="mt-6 space-y-2 relative z-10">
        <label htmlFor="targetRole" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          Target Role/Industry (Optional)
        </label>
        <input
          id="targetRole"
          type="text"
          value={targetRole}
          onChange={(e) => handleTargetRoleChange(e.target.value)}
          placeholder="e.g., Software Engineer, Product Manager, Data Scientist"
          className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-linkedin focus:border-transparent relative z-10 text-gray-900 dark:text-white bg-white dark:bg-gray-700"
          disabled={disabled}
          autoComplete="off"
        />
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Specify a target role to get more personalized optimization recommendations
        </p>
      </div>

      {/* Optimize Button */}
      <div className="mt-6">
        <button
          onClick={handleOptimizeClick}
          disabled={isOptimizeDisabled}
          className={`w-full px-6 py-3 rounded-lg font-medium transition-colors ${
            isOptimizeDisabled
              ? 'bg-gray-300 dark:bg-gray-600 text-gray-500 dark:text-gray-400 cursor-not-allowed'
              : 'bg-linkedin text-white hover:bg-linkedin-dark'
          }`}
        >
          {uploadState.isUploading ? (
            <div className="flex items-center justify-center space-x-2">
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              <span>{uploadState.status}</span>
            </div>
          ) : (
            '🚀 Optimize My LinkedIn Profile'
          )}
        </button>
      </div>
    </div>
  );
}