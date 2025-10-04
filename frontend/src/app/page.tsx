'use client';

import React, { useState } from 'react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import FileUpload from '@/components/FileUpload';
import ResultsDisplay from '@/components/ResultsDisplay';
import ThemeToggle from '@/components/ThemeToggle';
import { optimizeProfile, APIError } from '@/lib/api';
import { OptimizationResults, UploadState } from '@/types';
import { generateOptimizationId } from '@/lib/utils';
import logoBlack from '@/assets/otterlab-logo-wide-black.png';
import logoWhite from '@/assets/otterlab-logo-wide-white.png';

export default function HomePage() {
  const router = useRouter();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [targetRole, setTargetRole] = useState('');
  const [apiKey, setApiKey] = useState('');
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
    // FileUpload component handles all validation
    // This function is only called if validation passes

    // Generate optimization ID immediately
    const optimizationId = generateOptimizationId();

    // Redirect immediately to results page (don't wait for response)
    router.push(`/results?id=${optimizationId}`);

    // Start background processing (fire and forget)
    try {
      await optimizeProfile(selectedFile!, targetRole, optimizationId, apiKey);
    } catch (error) {
      console.error('Background optimization error:', error);
      // Error handling will be done on the results page through polling
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setTargetRole('');
    setApiKey('');
    setResults(null);
    setError('');
    setUploadState({
      isUploading: false,
      progress: 0,
      status: 'Ready to upload',
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow-sm border-b dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <a
              href="https://otterlab.dev/"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center px-4 py-2 hover:opacity-80 transition-opacity"
            >
              <Image
                src={logoBlack}
                alt="Otterlab"
                className="h-10 w-auto dark:hidden"
                priority
              />
              <Image
                src={logoWhite}
                alt="Otterlab"
                className="h-10 w-auto hidden dark:block"
                priority
              />
            </a>
            <div className="flex items-center space-x-3">
              <ThemeToggle />
              <a
                href="https://github.com/ndakic/linkedIn-profile-optimizer"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center space-x-2 px-4 py-2 text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors"
              >
                <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
                </svg>
                <span className="font-medium">View on GitHub</span>
              </a>
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
              <h2 className="text-4xl font-bold text-gray-900 dark:text-white">
                Optimize Your LinkedIn Profile with AI
              </h2>
              <p className="text-xl text-gray-600 dark:text-gray-300 max-w-3xl mx-auto">
                Upload your LinkedIn profile PDF and get personalized optimization
                recommendations plus content ideas to boost your professional presence.
              </p>
              <div className="flex justify-center space-x-8 text-sm text-gray-500 dark:text-gray-400">
                <div className="flex items-center">
                  <span className="text-green-500 dark:text-green-400 mr-2">✓</span>
                  AI-Powered Analysis
                </div>
                <div className="flex items-center">
                  <span className="text-green-500 dark:text-green-400 mr-2">✓</span>
                  Content Generation
                </div>
                <div className="flex items-center">
                  <span className="text-green-500 dark:text-green-400 mr-2">✓</span>
                  Industry Insights
                </div>
              </div>
            </div>


            {/* Upload Component */}
            <FileUpload
              onFileSelect={handleFileSelect}
              targetRole={targetRole}
              onTargetRoleChange={setTargetRole}
              apiKey={apiKey}
              onApiKeyChange={setApiKey}
              onOptimize={handleOptimize}
              uploadState={uploadState}
            />

            {/* How It Works */}
            <div className="bg-white dark:bg-gray-800 rounded-lg p-8 shadow-sm border dark:border-gray-700">
              <h3 className="text-2xl font-semibold text-gray-800 dark:text-white mb-6 text-center">
                How It Works
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="text-center space-y-3">
                  <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center mx-auto">
                    <span className="text-2xl">📄</span>
                  </div>
                  <h4 className="font-semibold text-gray-800 dark:text-white">1. Upload PDF</h4>
                  <p className="text-gray-600 dark:text-gray-300 text-sm">
                    Upload your LinkedIn profile PDF exported from LinkedIn
                  </p>
                </div>
                <div className="text-center space-y-3">
                  <div className="w-16 h-16 bg-green-100 dark:bg-green-900 rounded-full flex items-center justify-center mx-auto">
                    <span className="text-2xl">🤖</span>
                  </div>
                  <h4 className="font-semibold text-gray-800 dark:text-white">2. AI Analysis</h4>
                  <p className="text-gray-600 dark:text-gray-300 text-sm">
                    Our AI agents analyze your profile and identify optimization opportunities
                  </p>
                </div>
                <div className="text-center space-y-3">
                  <div className="w-16 h-16 bg-purple-100 dark:bg-purple-900 rounded-full flex items-center justify-center mx-auto">
                    <span className="text-2xl">🚀</span>
                  </div>
                  <h4 className="font-semibold text-gray-800 dark:text-white">3. Get Results</h4>
                  <p className="text-gray-600 dark:text-gray-300 text-sm">
                    Receive personalized recommendations and content ideas
                  </p>
                </div>
              </div>
            </div>
          </div>
        ) : results && (
          // Results Section
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
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
      <footer className="bg-white dark:bg-gray-800 border-t dark:border-gray-700 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center text-gray-500 dark:text-gray-400">
            <p>© 2025 Otterlab - LinkedIn Profile Optimizer. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}