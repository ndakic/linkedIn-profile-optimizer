'use client';

import React, { useState, useEffect } from 'react';
import Image from 'next/image';
import { useParams, useRouter } from 'next/navigation';
import ResultsDisplay from '@/components/ResultsDisplay';
import { OptimizationResults } from '@/types';

export default function ResultsPage() {
  const params = useParams();
  const router = useRouter();
  const [results, setResults] = useState<OptimizationResults | null>(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string>('');
  const [pollingCount, setPollingCount] = useState(0);
  const [progressData, setProgressData] = useState<any>(null);

  const optimizationId = params.id as string;

  useEffect(() => {
    if (optimizationId) {
      loadResultsWithPolling(optimizationId);
    }
  }, [optimizationId]);

  const loadResultsWithPolling = async (id: string) => {
    // First, try to load progress
    const progress = await loadProgress(id);

    if (progress) {
      setProgressData(progress);

      if (progress.status === 'completed') {
        // Optimization completed, try to load final results
        const result = await loadResults(id);
        if (result === true) {
          setProcessing(false);
          return;
        }
      } else if (progress.status === 'processing') {
        // Still processing - start polling
        setProcessing(true);
        setPollingCount(0);
        setLoading(false);
        startProgressPolling(id);
        return;
      }
    }

    // Fallback to old behavior if no progress found
    const result = await loadResults(id);
    if (result === null) {
      // Results not found yet - start processing state and polling
      setProcessing(true);
      setPollingCount(0);
      startPolling(id);
    } else if (result === true) {
      // Results found - stop any polling
      setProcessing(false);
    }
  };

  const startPolling = (id: string) => {
    const pollInterval = setInterval(async () => {
      setPollingCount(prev => prev + 1);

      const result = await loadResults(id, true); // Pass true for isPolling

      if (result === true) {
        // Results found - stop polling
        setProcessing(false);
        clearInterval(pollInterval);
      } else if (result === false) {
        // Error occurred - stop polling
        setProcessing(false);
        clearInterval(pollInterval);
      }

      // Stop polling after 10 minutes (120 polls at 5-second intervals)
      if (pollingCount >= 120) {
        setProcessing(false);
        setError('Processing is taking longer than expected. Please try refreshing the page or contact support.');
        clearInterval(pollInterval);
      }
    }, 5000); // Poll every 5 seconds

    // Cleanup interval on component unmount
    return () => clearInterval(pollInterval);
  };

  const startProgressPolling = (id: string) => {
    const pollInterval = setInterval(async () => {
      setPollingCount(prev => prev + 1);

      const progress = await loadProgress(id);

      if (progress) {
        setProgressData(progress);

        if (progress.status === 'completed') {
          // Optimization completed, try to load final results
          const result = await loadResults(id, true);
          if (result === true) {
            setProcessing(false);
            clearInterval(pollInterval);
          }
        } else if (progress.status === 'failed') {
          // Optimization failed
          setProcessing(false);
          setError('Optimization failed. Please try again.');
          clearInterval(pollInterval);
        }
      }

      // Stop polling after 10 minutes (120 polls at 5-second intervals)
      if (pollingCount >= 120) {
        setProcessing(false);
        setError('Processing is taking longer than expected. Please try refreshing the page or contact support.');
        clearInterval(pollInterval);
      }
    }, 5000); // Poll every 5 seconds for progress

    // Cleanup interval on component unmount
    return () => clearInterval(pollInterval);
  };

  const loadResults = async (id: string, isPolling: boolean = false) => {
    try {
      // Only set loading to true on initial load, not during polling
      if (!isPolling) {
        setLoading(true);
        setError('');
      }

      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      const response = await fetch(`${backendUrl}/results/${id}`);

      if (!response.ok) {
        if (response.status === 404) {
          // Results not found yet - might still be processing
          setResults(null);
          if (!isPolling) {
            setLoading(false);
          }
          return null; // Indicate results not found yet
        } else {
          setError('Failed to load optimization results. Please try again later.');
          setLoading(false);
          setProcessing(false);
          return false; // Indicate error
        }
      }

      const data = await response.json();
      setResults(data);
      setLoading(false);
      setProcessing(false);
      return true; // Indicate success
    } catch (error) {
      console.error('Error loading results:', error);
      setError('An error occurred while loading the results. Please check your connection and try again.');
      setLoading(false);
      setProcessing(false);
      return false; // Indicate error
    }
  };

  const loadProgress = async (id: string) => {
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      const response = await fetch(`${backendUrl}/progress/${id}`);

      if (!response.ok) {
        if (response.status === 404) {
          return null; // Progress not found yet
        } else {
          throw new Error('Failed to load progress');
        }
      }

      const progressData = await response.json();
      return progressData;
    } catch (error) {
      console.error('Error loading progress:', error);
      return null;
    }
  };

  const handleNewOptimization = () => {
    router.push('/');
  };

  const handleCopyUrl = () => {
    navigator.clipboard.writeText(window.location.href);
    // You could add a toast notification here
  };

  const renderProcessingSteps = () => {
    const steps = [
      {
        key: 'optimization_started',
        label: 'Initialization',
        description: 'Setting up optimization...'
      },
      {
        key: 'profile_extraction',
        label: 'Profile Extraction',
        description: 'Parsing PDF and extracting data...'
      },
      {
        key: 'profile_analysis',
        label: 'AI Analysis',
        description: 'Analyzing profile with AI...'
      },
      {
        key: 'content_generation',
        label: 'Content Generation',
        description: 'Creating personalized content...'
      },
      {
        key: 'optimization_completed',
        label: 'Completion',
        description: 'Finalizing results...'
      }
    ];

    const completedSteps = progressData?.completed_steps || [];
    const currentStep = progressData?.current_step;

    return steps.map((step, index) => {
      const isCompleted = completedSteps.includes(step.key);
      const isCurrent = currentStep === step.key;
      const isPending = !isCompleted && !isCurrent;

      let statusIcon = '⏳';
      let statusClass = 'text-gray-500';
      let indicatorClass = 'bg-gray-300';

      if (isCompleted) {
        statusIcon = '✅';
        statusClass = 'text-green-700';
        indicatorClass = 'bg-green-500';
      } else if (isCurrent) {
        statusIcon = '🔄';
        statusClass = 'text-linkedin';
        indicatorClass = 'bg-linkedin animate-pulse';
      }

      return (
        <div key={step.key} className="flex items-center">
          <div className={`w-2 h-2 ${indicatorClass} rounded-full mr-3`}></div>
          <div className="flex-1">
            <div className={`${statusClass} font-medium`}>
              {statusIcon} {step.label}
            </div>
            {(isCurrent || isCompleted) && (
              <div className="text-xs text-gray-500 mt-1">
                {step.description}
              </div>
            )}
          </div>
        </div>
      );
    });
  };

  if (loading || processing) {
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

        {/* Loading/Processing Content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex flex-col items-center justify-center min-h-96 space-y-4">
            <div className="w-16 h-16 border-4 border-linkedin border-t-transparent rounded-full animate-spin"></div>

            {loading ? (
              <>
                <h2 className="text-2xl font-semibold text-gray-800">Loading Results...</h2>
                <p className="text-gray-600">Retrieving optimization results for ID: {optimizationId}</p>
              </>
            ) : (
              <>
                <h2 className="text-2xl font-semibold text-gray-800">Processing Your Profile...</h2>
                <p className="text-gray-600">Your LinkedIn profile is being optimized</p>
                <p className="text-sm text-gray-500">ID: {optimizationId}</p>

                {/* Processing Steps */}
                <div className="bg-white rounded-lg p-6 shadow-sm border max-w-md w-full mt-6">
                  <h3 className="text-lg font-semibold text-gray-800 mb-4">Optimization Steps</h3>

                  {progressData && (
                    <div className="mb-4">
                      <div className="flex justify-between text-sm text-gray-600 mb-1">
                        <span>Progress</span>
                        <span>{progressData.progress_percentage}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-linkedin h-2 rounded-full transition-all duration-300"
                          style={{ width: `${progressData.progress_percentage}%` }}
                        />
                      </div>
                    </div>
                  )}

                  <div className="space-y-3">
                    {renderProcessingSteps()}
                  </div>

                  <div className="mt-4 text-center">
                    {progressData?.estimated_remaining_seconds > 0 && (
                      <p className="text-sm text-gray-500">
                        Estimated remaining: {Math.ceil(progressData.estimated_remaining_seconds / 60)} minutes
                      </p>
                    )}
                    {pollingCount > 0 && (
                      <p className="text-xs text-gray-400 mt-1">
                        Checking for updates ({pollingCount}/120)
                      </p>
                    )}
                  </div>
                </div>
              </>
            )}
          </div>
        </main>
      </div>
    );
  }

  if (error) {
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

        {/* Error Content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="space-y-6">
            <div className="bg-red-50 border border-red-200 rounded-lg p-6">
              <div className="flex items-center">
                <div className="text-2xl mr-3">❌</div>
                <div>
                  <h2 className="text-xl font-semibold text-red-800 mb-2">
                    Unable to Load Results
                  </h2>
                  <p className="text-red-600 mb-4">{error}</p>
                  <div className="space-x-4">
                    <button
                      onClick={() => loadResults(optimizationId)}
                      className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                    >
                      Try Again
                    </button>
                    <button
                      onClick={handleNewOptimization}
                      className="px-4 py-2 bg-linkedin text-white rounded-lg hover:bg-linkedin-dark transition-colors"
                    >
                      New Optimization
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    );
  }

  if (!results) {
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

        {/* No Results Content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex flex-col items-center justify-center min-h-96 space-y-4">
            <div className="text-6xl">🔍</div>
            <h2 className="text-2xl font-semibold text-gray-800">No Results Found</h2>
            <p className="text-gray-600 text-center max-w-md">
              The optimization results for ID "{optimizationId}" could not be found.
            </p>
            <button
              onClick={handleNewOptimization}
              className="px-6 py-3 bg-linkedin text-white rounded-lg hover:bg-linkedin-dark transition-colors"
            >
              Start New Optimization
            </button>
          </div>
        </main>
      </div>
    );
  }

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
        <div className="space-y-6">
          {/* Header with actions */}
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                LinkedIn Profile Optimization Results
              </h1>
              <p className="text-gray-600 mt-2">
                Results ID: <span className="font-mono text-sm bg-gray-100 px-2 py-1 rounded">{optimizationId}</span>
              </p>
              {results.storage_info?.created_at && (
                <p className="text-gray-500 text-sm mt-1">
                  Generated: {new Date(results.storage_info.created_at).toLocaleString()}
                </p>
              )}
              {results.token_usage && (
                <div className="text-gray-500 text-sm mt-2 flex items-center gap-4">
                  <span className="flex items-center">
                    🤖 <span className="ml-1 font-medium">Model:</span>
                    <span className="ml-1 font-mono bg-blue-50 px-2 py-0.5 rounded text-blue-700">{results.token_usage.model}</span>
                  </span>
                  <span className="flex items-center">
                    📊 <span className="ml-1 font-medium">Tokens:</span>
                    <span className="ml-1 font-mono bg-green-50 px-2 py-0.5 rounded text-green-700">
                      {results.token_usage.total_tokens.toLocaleString()}
                    </span>
                    <span className="ml-1 text-xs text-gray-400">
                      (Input: {results.token_usage.prompt_tokens.toLocaleString()} | Output: {results.token_usage.completion_tokens.toLocaleString()})
                    </span>
                  </span>
                </div>
              )}
            </div>
            <div className="flex space-x-3">
              <button
                onClick={handleCopyUrl}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
              >
                📋 Copy URL
              </button>
              <button
                onClick={handleNewOptimization}
                className="px-4 py-2 bg-linkedin text-white rounded-lg hover:bg-linkedin-dark transition-colors"
              >
                New Optimization
              </button>
            </div>
          </div>

          {/* Results Display */}
          <ResultsDisplay results={results} />
        </div>
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