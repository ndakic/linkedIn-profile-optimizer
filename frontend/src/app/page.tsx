'use client';

import React, { useState } from 'react';
import Image from 'next/image';
import FileUpload from '@/components/FileUpload';
import ResultsDisplay from '@/components/ResultsDisplay';
import { optimizeProfile, APIError } from '@/lib/api';
import { OptimizationResults, UploadState } from '@/types';

export default function HomePage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [targetRole, setTargetRole] = useState('');
  const [uploadState, setUploadState] = useState<UploadState>({
    isUploading: false,
    progress: 0,
    status: 'Ready to upload',
  });
  const [results, setResults] = useState<OptimizationResults | null>(null);
  const [error, setError] = useState<string>('');

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    setResults(null);
    setError('');
  };

  const handleOptimize = async () => {
    if (!selectedFile) return;

    setError('');
    setResults(null);
    setUploadState({
      isUploading: true,
      progress: 0,
      status: 'Uploading file...',
    });

    try {
      // Simulate upload progress
      const progressSteps = [
        { progress: 20, status: 'Processing PDF...' },
        { progress: 40, status: 'Extracting profile data...' },
        { progress: 60, status: 'Analyzing profile...' },
        { progress: 80, status: 'Generating content ideas...' },
        { progress: 95, status: 'Finalizing results...' },
      ];

      for (const step of progressSteps) {
        setUploadState(prev => ({
          ...prev,
          progress: step.progress,
          status: step.status,
        }));
        await new Promise(resolve => setTimeout(resolve, 500));
      }

      const optimizationResults = await optimizeProfile(selectedFile, targetRole);

      setUploadState({
        isUploading: false,
        progress: 100,
        status: 'Optimization complete!',
      });

      setResults(optimizationResults);

    } catch (error) {
      console.error('Optimization error:', error);

      let errorMessage = 'An unexpected error occurred';

      if (error instanceof APIError) {
        errorMessage = error.message;
      } else if (error instanceof Error) {
        errorMessage = error.message;
      }

      setError(errorMessage);
      setUploadState({
        isUploading: false,
        progress: 0,
        status: 'Upload failed',
      });
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setTargetRole('');
    setResults(null);
    setError('');
    setUploadState({
      isUploading: false,
      progress: 0,
      status: 'Ready to upload',
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Image
                src="/assets/otterlab-logo.png"
                alt="Otterlab"
                width={140}
                height={70}
                className="rounded-lg"
              />
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {!results && !error ? (
          // Upload Section
          <div className="space-y-8">
            {/* Hero Section */}
            <div className="text-center space-y-4">
              <h2 className="text-4xl font-bold text-gray-900">
                Optimize Your LinkedIn Profile with AI
              </h2>
              <p className="text-xl text-gray-600 max-w-3xl mx-auto">
                Upload your LinkedIn profile PDF and get personalized optimization
                recommendations plus content ideas to boost your professional presence.
              </p>
              <div className="flex justify-center space-x-8 text-sm text-gray-500">
                <div className="flex items-center">
                  <span className="text-green-500 mr-2">✓</span>
                  AI-Powered Analysis
                </div>
                <div className="flex items-center">
                  <span className="text-green-500 mr-2">✓</span>
                  Content Generation
                </div>
                <div className="flex items-center">
                  <span className="text-green-500 mr-2">✓</span>
                  Industry Insights
                </div>
              </div>
            </div>

            {/* Upload Component */}
            <FileUpload
              onFileSelect={handleFileSelect}
              targetRole={targetRole}
              onTargetRoleChange={setTargetRole}
              onOptimize={handleOptimize}
              uploadState={uploadState}
            />

            {/* How It Works */}
            <div className="bg-white rounded-lg p-8 shadow-sm border">
              <h3 className="text-2xl font-semibold text-gray-800 mb-6 text-center">
                How It Works
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="text-center space-y-3">
                  <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto">
                    <span className="text-2xl">📄</span>
                  </div>
                  <h4 className="font-semibold text-gray-800">1. Upload PDF</h4>
                  <p className="text-gray-600 text-sm">
                    Upload your LinkedIn profile PDF exported from LinkedIn
                  </p>
                </div>
                <div className="text-center space-y-3">
                  <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto">
                    <span className="text-2xl">🤖</span>
                  </div>
                  <h4 className="font-semibold text-gray-800">2. AI Analysis</h4>
                  <p className="text-gray-600 text-sm">
                    Our AI agents analyze your profile and identify optimization opportunities
                  </p>
                </div>
                <div className="text-center space-y-3">
                  <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto">
                    <span className="text-2xl">🚀</span>
                  </div>
                  <h4 className="font-semibold text-gray-800">3. Get Results</h4>
                  <p className="text-gray-600 text-sm">
                    Receive personalized recommendations and content ideas
                  </p>
                </div>
              </div>
            </div>
          </div>
        ) : error ? (
          // Error Section
          <div className="space-y-6">
            <div className="bg-red-50 border border-red-200 rounded-lg p-6">
              <div className="flex items-center">
                <div className="text-2xl mr-3">❌</div>
                <div>
                  <h2 className="text-xl font-semibold text-red-800 mb-2">
                    Optimization Failed
                  </h2>
                  <p className="text-red-600 mb-4">{error}</p>
                  <button
                    onClick={handleReset}
                    className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                  >
                    Try Again
                  </button>
                </div>
              </div>
            </div>
          </div>
        ) : results && (
          // Results Section
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-3xl font-bold text-gray-900">
                Optimization Results
              </h2>
              <button
                onClick={handleReset}
                className="px-4 py-2 bg-linkedin text-white rounded-lg hover:bg-linkedin-dark transition-colors"
              >
                Optimize Another Profile
              </button>
            </div>
            <ResultsDisplay results={results} />
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center text-gray-500">
            <p>© 2025 Otterlab - LinkedIn Profile Optimizer. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}