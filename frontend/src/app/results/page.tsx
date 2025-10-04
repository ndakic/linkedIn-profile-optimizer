'use client';

import React, { useState, useEffect, Suspense } from 'react';
import Image from 'next/image';
import { useSearchParams, useRouter } from 'next/navigation';
import ResultsDisplay from '@/components/ResultsDisplay';
import ThemeToggle from '@/components/ThemeToggle';
import { OptimizationResults } from '@/types';
import { isApiKeyError } from '@/lib/utils';
import logoBlack from '@/assets/otterlab-logo-wide-black.png';
import logoWhite from '@/assets/otterlab-logo-wide-white.png';

function ResultsContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [results, setResults] = useState<OptimizationResults | null>(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string>('');
  const [pollingCount, setPollingCount] = useState(0);
  const [progressData, setProgressData] = useState<any>(null);

  const optimizationId = searchParams.get('id') || '';

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
        // Don't show error - just stop processing
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
          // Optimization failed - check if it's API key related
          let errorMessage = progress.error;

          // Check step_details for error messages
          if (!errorMessage && progress.step_details) {
            for (const [stepName, stepInfo] of Object.entries(progress.step_details)) {
              const stepData = stepInfo as any;
              if (stepData.data?.error) {
                errorMessage = stepData.data.error;
                break;
              }
            }
          }

          if (errorMessage) {
            console.log('Failed status error:', errorMessage);
            const isApiError = isApiKeyError(errorMessage, progress);
            console.log('Is API key error:', isApiError);

            if (isApiError) {
              console.log('Setting API key error state from failed status');
              setError('Invalid API key. Please check your OpenAI API key and try again.');
              setLoading(false);
            }
          }
          setProcessing(false);
          clearInterval(pollInterval);
        }
      }

      // Stop polling after 10 minutes (120 polls at 5-second intervals)
      if (pollingCount >= 120) {
        setProcessing(false);
        // Don't show error - just stop processing
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
          // Check if it's an API key error
          const errorData = await response.json().catch(() => ({}));
          const errorMessage = errorData.detail || errorData.message || response.statusText;

          if (isApiKeyError(errorMessage, { status: response.status, ...errorData })) {
            setError('Invalid API key. Please check your OpenAI API key and try again.');
          }

          setLoading(false);
          setProcessing(false);
          return false; // Indicate error
        }
      }

      const data = await response.json();

      // Debug: log results data structure
      console.log('Results data:', data);

      // Check multiple locations for errors
      let errorMessage = null;

      // Check top-level error
      if (data.error) {
        errorMessage = data.error;
      }

      // Check if it's in the response detail
      if (data.detail) {
        errorMessage = data.detail;
      }

      // Check nested error structures
      if (data.final_results?.error) {
        errorMessage = data.final_results.error;
      }

      // If we found an error, check if it's API key related
      if (errorMessage) {
        console.log('Found error in results:', errorMessage);
        const isApiError = isApiKeyError(errorMessage, data);
        console.log('Is API key error:', isApiError);

        if (isApiError) {
          console.log('Setting API key error state');
          setError('Invalid API key. Please check your OpenAI API key and try again.');
          setLoading(false);
        }
        setProcessing(false);
      }

      setResults(data);
      setLoading(false);
      setProcessing(false);
      return true; // Indicate success
    } catch (error) {
      console.error('Error loading results:', error);
      // Silently handle error (unless it's API key related, which was checked above)
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
          // Check if it's an API key error
          const errorData = await response.json().catch(() => ({}));
          const errorMessage = errorData.detail || errorData.message || response.statusText;

          if (isApiKeyError(errorMessage, { status: response.status, ...errorData })) {
            setError('Invalid API key. Please check your OpenAI API key and try again.');
            setProcessing(false);
          }

          throw new Error('Failed to load progress');
        }
      }

      const progressData = await response.json();

      // Debug: log progress data structure
      console.log('Progress data:', progressData);

      // Check multiple locations for errors
      let errorMessage = null;

      // Check top-level error
      if (progressData.error) {
        errorMessage = progressData.error;
      }

      // Check step_details for errors in any step
      if (progressData.step_details) {
        for (const [stepName, stepInfo] of Object.entries(progressData.step_details)) {
          const stepData = stepInfo as any;
          if (stepData.data?.error) {
            errorMessage = stepData.data.error;
            break;
          }
        }
      }

      // Check if results contain an error
      if (progressData.results) {
        try {
          const results = typeof progressData.results === 'string'
            ? JSON.parse(progressData.results)
            : progressData.results;
          if (results.error) {
            errorMessage = results.error;
          }
        } catch (e) {
          // Ignore JSON parse errors
        }
      }

      // If we found an error, check if it's API key related
      if (errorMessage) {
        console.log('Found error in progress:', errorMessage);
        const isApiError = isApiKeyError(errorMessage, progressData);
        console.log('Is API key error:', isApiError);

        if (isApiError) {
          console.log('Setting API key error state');
          setError('Invalid API key. Please check your OpenAI API key and try again.');
          setProcessing(false);
          setLoading(false);
        }
      }

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
      let statusClass = 'text-gray-500 dark:text-gray-400';
      let indicatorClass = 'bg-gray-300 dark:bg-gray-600';

      if (isCompleted) {
        statusIcon = '✅';
        statusClass = 'text-green-700 dark:text-green-400';
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
              <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
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

        {/* Loading/Processing Content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex flex-col items-center justify-center min-h-96 space-y-4">
            <div className="w-16 h-16 border-4 border-linkedin border-t-transparent rounded-full animate-spin"></div>

            {loading ? (
              <>
                <h2 className="text-2xl font-semibold text-gray-800 dark:text-white">Loading Results...</h2>
                <p className="text-gray-600 dark:text-gray-300">Retrieving optimization results for ID: {optimizationId}</p>
              </>
            ) : (
              <>
                <h2 className="text-2xl font-semibold text-gray-800 dark:text-white">Processing Your Profile...</h2>
                <p className="text-gray-600 dark:text-gray-300">Your LinkedIn profile is being optimized</p>
                <p className="text-sm text-gray-500 dark:text-gray-400">ID: {optimizationId}</p>

                {/* Processing Steps */}
                <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border dark:border-gray-700 max-w-md w-full mt-6">
                  <h3 className="text-lg font-semibold text-gray-800 dark:text-white mb-4">Optimization Steps</h3>

                  {progressData && (
                    <div className="mb-4">
                      <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-1">
                        <span>Progress</span>
                        <span>{progressData.progress_percentage}%</span>
                      </div>
                      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
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
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        Estimated remaining: {Math.ceil(progressData.estimated_remaining_seconds / 60)} minutes
                      </p>
                    )}
                    {pollingCount > 0 && (
                      <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
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

  // Show error page if there's an API key error
  if (error) {
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

        {/* Error Content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="space-y-6">
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
              <div className="flex items-center">
                <div className="text-2xl mr-3">❌</div>
                <div>
                  <h2 className="text-xl font-semibold text-red-800 dark:text-red-300 mb-2">
                    API Key Error
                  </h2>
                  <p className="text-red-600 dark:text-red-400 mb-4">{error}</p>
                  <button
                    onClick={handleNewOptimization}
                    className="px-4 py-2 bg-linkedin text-white rounded-lg hover:bg-linkedin-dark transition-colors"
                  >
                    Try Again with Different API Key
                  </button>
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

        {/* No Results Content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex flex-col items-center justify-center min-h-96 space-y-4">
            <div className="text-6xl">🔍</div>
            <h2 className="text-2xl font-semibold text-gray-800 dark:text-white">No Results Found</h2>
            <p className="text-gray-600 dark:text-gray-300 text-center max-w-md">
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
        <div className="space-y-6">
          {/* Header Section */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-6">
              {/* Title and Meta */}
              <div className="flex-1">
                <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-4">
                  LinkedIn Profile Optimization Results
                </h1>

                {/* Meta Information Grid */}
                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-gray-500 dark:text-gray-400">Results ID:</span>
                    <span className="font-mono text-xs sm:text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 px-3 py-1 rounded">
                      {optimizationId}
                    </span>
                  </div>

                  {results.storage_info?.created_at && (
                    <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                      <span>Generated:</span>
                      <span>{new Date(results.storage_info.created_at).toLocaleString()}</span>
                    </div>
                  )}

                  {results.token_usage && (
                    <div className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-6 text-sm">
                      <div className="flex items-center gap-2">
                        <span className="text-gray-500 dark:text-gray-400">🤖 Model:</span>
                        <span className="font-mono text-xs bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 px-2 py-1 rounded">
                          {results.token_usage.model}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-gray-500 dark:text-gray-400">📊 Tokens:</span>
                        <span className="font-mono text-xs bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-300 px-2 py-1 rounded">
                          {results.token_usage.total_tokens.toLocaleString()}
                        </span>
                        <span className="text-xs text-gray-400 dark:text-gray-500">
                          ({results.token_usage.prompt_tokens.toLocaleString()} in / {results.token_usage.completion_tokens.toLocaleString()} out)
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row gap-3 lg:flex-shrink-0">
                <button
                  onClick={handleCopyUrl}
                  className="flex items-center justify-center gap-2 px-4 py-2.5 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors font-medium text-sm whitespace-nowrap"
                >
                  <span>📋</span>
                  <span>Copy URL</span>
                </button>
                <button
                  onClick={handleNewOptimization}
                  className="flex items-center justify-center gap-2 px-4 py-2.5 bg-linkedin text-white rounded-lg hover:bg-linkedin-dark transition-colors font-medium text-sm whitespace-nowrap"
                >
                  <span>+</span>
                  <span>New Optimization</span>
                </button>
              </div>
            </div>
          </div>

          {/* Results Display */}
          <ResultsDisplay results={results} />
        </div>
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

export default function ResultsPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center">
        <div className="w-16 h-16 border-4 border-linkedin border-t-transparent rounded-full animate-spin"></div>
      </div>
    }>
      <ResultsContent />
    </Suspense>
  );
}