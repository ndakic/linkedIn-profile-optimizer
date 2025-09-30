'use client';

import React, { useState } from 'react';
import { OptimizationResults } from '@/types';

interface ResultsDisplayProps {
  results: OptimizationResults;
}

export default function ResultsDisplay({ results }: ResultsDisplayProps) {
  const [activeTab, setActiveTab] = useState('overview');

  if (!results.success) {
    return (
      <div className="max-w-4xl mx-auto p-6 bg-red-50 border border-red-200 rounded-lg">
        <h2 className="text-xl font-semibold text-red-800 mb-2">
          ❌ Optimization Failed
        </h2>
        <p className="text-red-600">{results.error || 'Unknown error occurred'}</p>
        <p className="text-sm text-red-500 mt-2">Status: {results.status}</p>
      </div>
    );
  }

  const tabs = [
    { id: 'overview', label: 'Overview', icon: '📊' },
    { id: 'analysis', label: 'Profile Analysis', icon: '🔍' },
    { id: 'content', label: 'Content Ideas', icon: '✍️' },
    { id: 'recommendations', label: 'Recommendations', icon: '💡' },
  ];

  return (
    <div className="max-w-6xl mx-auto">
      {/* Success Header */}
      <div className="bg-green-50 border border-green-200 rounded-lg p-6 mb-6">
        <h2 className="text-2xl font-bold text-green-800 mb-2">
          ✅ LinkedIn Profile Optimization Complete!
        </h2>
        <p className="text-green-600">{results.status}</p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab.id
                  ? 'border-linkedin text-linkedin'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <span className="mr-2">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="space-y-6">
        {activeTab === 'overview' && (
          <OverviewTab results={results} />
        )}

        {activeTab === 'analysis' && results.analysis_results && (
          <AnalysisTab analysis={results.analysis_results} />
        )}

        {activeTab === 'content' && results.content_results && (
          <ContentTab content={results.content_results} />
        )}

        {activeTab === 'recommendations' && results.analysis_results && (
          <RecommendationsTab analysis={results.analysis_results} />
        )}
      </div>
    </div>
  );
}

function OverviewTab({ results }: { results: OptimizationResults }) {
  const { summary, analysis_results, content_results } = results;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {/* Profile Score */}
      <div className="bg-white p-6 rounded-lg border shadow-sm">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">
          📈 Profile Score
        </h3>
        <div className="text-center">
          <div className="text-4xl font-bold text-linkedin mb-2">
            {analysis_results?.overall_score || 0}/100
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3">
            <div
              className="bg-linkedin h-3 rounded-full transition-all duration-300"
              style={{ width: `${analysis_results?.overall_score || 0}%` }}
            />
          </div>
        </div>
      </div>

      {/* Completeness */}
      <div className="bg-white p-6 rounded-lg border shadow-sm">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">
          ✅ Profile Completeness
        </h3>
        <div className="text-center">
          <div className="text-4xl font-bold text-green-600 mb-2">
            {summary?.profile_completeness || 0}%
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3">
            <div
              className="bg-green-600 h-3 rounded-full transition-all duration-300"
              style={{ width: `${summary?.profile_completeness || 0}%` }}
            />
          </div>
        </div>
      </div>

      {/* Content Generated */}
      <div className="bg-white p-6 rounded-lg border shadow-sm">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">
          🎯 Content Generated
        </h3>
        <div className="space-y-2">
          <div className="flex justify-between">
            <span className="text-gray-600">Ideas:</span>
            <span className="font-semibold">
              {content_results?.content_ideas?.length || 0}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Sample Posts:</span>
            <span className="font-semibold">
              {content_results?.sample_posts?.length || 0}
            </span>
          </div>
        </div>
      </div>

      {/* Key Improvements */}
      <div className="bg-white p-6 rounded-lg border shadow-sm md:col-span-2 lg:col-span-3">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">
          🎯 Priority Actions
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <h4 className="font-medium text-gray-700 mb-2">Top Improvements:</h4>
            <ul className="space-y-1">
              {(summary?.key_improvements || []).slice(0, 3).map((improvement, index) => (
                <li key={index} className="text-sm text-gray-600 flex items-start">
                  <span className="text-linkedin mr-2">•</span>
                  {improvement}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h4 className="font-medium text-gray-700 mb-2">Recommended Actions:</h4>
            <ul className="space-y-1">
              {(summary?.recommended_actions || []).slice(0, 3).map((action, index) => (
                <li key={index} className="text-sm text-gray-600 flex items-start">
                  <span className="text-linkedin mr-2">•</span>
                  {action}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

function AnalysisTab({ analysis }: { analysis: any }) {
  return (
    <div className="space-y-6">
      {/* Strengths and Areas for Improvement */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-green-50 p-6 rounded-lg border border-green-200">
          <h3 className="text-lg font-semibold text-green-800 mb-4">
            ✨ Strengths
          </h3>
          <ul className="space-y-2">
            {(analysis.strengths || []).map((strength: string, index: number) => (
              <li key={index} className="text-green-700 flex items-start">
                <span className="text-green-500 mr-2">✓</span>
                {strength}
              </li>
            ))}
          </ul>
        </div>

        <div className="bg-yellow-50 p-6 rounded-lg border border-yellow-200">
          <h3 className="text-lg font-semibold text-yellow-800 mb-4">
            🔧 Areas for Improvement
          </h3>
          <ul className="space-y-2">
            {(analysis.areas_for_improvement || []).map((area: string, index: number) => (
              <li key={index} className="text-yellow-700 flex items-start">
                <span className="text-yellow-500 mr-2">⚠</span>
                {area}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Industry Insights */}
      {analysis.industry_insights && (
        <div className="bg-blue-50 p-6 rounded-lg border border-blue-200">
          <h3 className="text-lg font-semibold text-blue-800 mb-4">
            🏭 Industry Insights
          </h3>
          <p className="text-blue-700">{analysis.industry_insights}</p>
        </div>
      )}

      {/* Next Steps */}
      <div className="bg-white p-6 rounded-lg border shadow-sm">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">
          🚀 Next Steps
        </h3>
        <ul className="space-y-2">
          {(analysis.next_steps || []).map((step: string, index: number) => (
            <li key={index} className="text-gray-700 flex items-start">
              <span className="text-linkedin mr-2 font-semibold">{index + 1}.</span>
              {step}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function ContentTab({ content }: { content: any }) {
  const [activeContentTab, setActiveContentTab] = useState('ideas');

  return (
    <div className="space-y-6">
      {/* Content Strategy */}
      <div className="bg-linkedin text-white p-6 rounded-lg">
        <h3 className="text-xl font-semibold mb-4">📋 Content Strategy</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <h4 className="font-medium mb-2">Posting Frequency:</h4>
            <p className="text-blue-100">
              {content.content_strategy?.posting_frequency || 'Not specified'}
            </p>
          </div>
          <div>
            <h4 className="font-medium mb-2">Best Times:</h4>
            <ul className="text-blue-100 text-sm">
              {(content.content_strategy?.best_posting_times || []).map(
                (time: string, index: number) => (
                  <li key={index}>• {time}</li>
                )
              )}
            </ul>
          </div>
          <div className="md:col-span-2">
            <h4 className="font-medium mb-2">Content Pillars:</h4>
            <div className="flex flex-wrap gap-2">
              {(content.content_strategy?.content_pillars || []).map(
                (pillar: string, index: number) => (
                  <span
                    key={index}
                    className="px-3 py-1 bg-blue-600 rounded-full text-sm"
                  >
                    {pillar}
                  </span>
                )
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Content Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveContentTab('ideas')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeContentTab === 'ideas'
                ? 'border-linkedin text-linkedin'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            💡 Content Ideas ({content.content_ideas?.length || 0})
          </button>
          <button
            onClick={() => setActiveContentTab('posts')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeContentTab === 'posts'
                ? 'border-linkedin text-linkedin'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            📝 Sample Posts ({content.sample_posts?.length || 0})
          </button>
        </nav>
      </div>

      {/* Content Ideas */}
      {activeContentTab === 'ideas' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {(content.content_ideas || []).map((idea: any, index: number) => (
            <div key={index} className="bg-white p-6 rounded-lg border shadow-sm">
              <div className="flex justify-between items-start mb-3">
                <h4 className="font-semibold text-gray-800">{idea.topic}</h4>
                <span className="px-2 py-1 bg-gray-100 text-xs rounded text-gray-600">
                  {idea.type}
                </span>
              </div>
              <p className="text-gray-600 text-sm mb-3">{idea.objective}</p>
              <p className="text-gray-700 mb-3">{idea.content}</p>
              <div className="space-y-2">
                <div>
                  <span className="text-xs font-medium text-gray-500">Target:</span>
                  <span className="text-xs text-gray-600 ml-1">{idea.target_audience}</span>
                </div>
                <div>
                  <span className="text-xs font-medium text-gray-500">CTA:</span>
                  <span className="text-xs text-gray-600 ml-1">{idea.call_to_action}</span>
                </div>
                {idea.hashtags && idea.hashtags.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {idea.hashtags.map((tag: string, i: number) => (
                      <span key={i} className="text-xs text-linkedin">
                        #{tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Sample Posts */}
      {activeContentTab === 'posts' && (
        <div className="space-y-6">
          {(content.sample_posts || []).map((post: any, index: number) => (
            <div key={index} className="bg-white p-6 rounded-lg border shadow-sm">
              <h4 className="font-semibold text-gray-800 mb-3">{post.title}</h4>
              <div className="bg-gray-50 p-4 rounded mb-4">
                <p className="text-gray-700 whitespace-pre-wrap">{post.content}</p>
              </div>
              {post.hashtags && post.hashtags.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-3">
                  {post.hashtags.map((tag: string, i: number) => (
                    <span key={i} className="text-sm text-linkedin">
                      #{tag}
                    </span>
                  ))}
                </div>
              )}
              {post.engagement_hooks && post.engagement_hooks.length > 0 && (
                <div>
                  <h5 className="text-sm font-medium text-gray-700 mb-2">
                    Engagement Hooks:
                  </h5>
                  <ul className="text-sm text-gray-600">
                    {post.engagement_hooks.map((hook: string, i: number) => (
                      <li key={i} className="flex items-start">
                        <span className="text-linkedin mr-2">•</span>
                        {hook}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function RecommendationsTab({ analysis }: { analysis: any }) {
  const { recommendations } = analysis;

  return (
    <div className="space-y-6">
      {/* Headline Optimization */}
      {recommendations.headline && (
        <div className="bg-white p-6 rounded-lg border shadow-sm">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">
            📝 Headline Optimization
          </h3>
          <div className="space-y-4">
            <div>
              <h4 className="font-medium text-red-600 mb-2">Current:</h4>
              <p className="text-gray-700 bg-red-50 p-3 rounded">
                {recommendations.headline.current || 'Not provided'}
              </p>
            </div>
            <div>
              <h4 className="font-medium text-green-600 mb-2">Suggested:</h4>
              <p className="text-gray-700 bg-green-50 p-3 rounded">
                {recommendations.headline.suggested}
              </p>
            </div>
            <div>
              <h4 className="font-medium text-blue-600 mb-2">Why this works:</h4>
              <p className="text-gray-700 bg-blue-50 p-3 rounded">
                {recommendations.headline.reasoning}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Summary Optimization */}
      {recommendations.summary && (
        <div className="bg-white p-6 rounded-lg border shadow-sm">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">
            📄 Summary Optimization
          </h3>
          <div className="space-y-4">
            <div>
              <h4 className="font-medium text-red-600 mb-2">Current:</h4>
              <p className="text-gray-700 bg-red-50 p-3 rounded text-sm">
                {recommendations.summary.current || 'Not provided'}
              </p>
            </div>
            <div>
              <h4 className="font-medium text-green-600 mb-2">Suggested:</h4>
              <p className="text-gray-700 bg-green-50 p-3 rounded text-sm">
                {recommendations.summary.suggested}
              </p>
            </div>
            <div>
              <h4 className="font-medium text-blue-600 mb-2">Why this works:</h4>
              <p className="text-gray-700 bg-blue-50 p-3 rounded text-sm">
                {recommendations.summary.reasoning}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Skills Recommendations */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg border shadow-sm">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">
            ➕ Skills to Add
          </h3>
          <ul className="space-y-2">
            {(recommendations.skills_to_add || []).map((skill: string, index: number) => (
              <li key={index} className="text-gray-700 flex items-center">
                <span className="text-green-500 mr-2">+</span>
                {skill}
              </li>
            ))}
          </ul>
        </div>

        <div className="bg-white p-6 rounded-lg border shadow-sm">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">
            ⭐ Skills to Emphasize
          </h3>
          <ul className="space-y-2">
            {(recommendations.skills_to_emphasize || []).map((skill: string, index: number) => (
              <li key={index} className="text-gray-700 flex items-center">
                <span className="text-yellow-500 mr-2">⭐</span>
                {skill}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Keywords and Certifications */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg border shadow-sm">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">
            🔑 Keywords to Include
          </h3>
          <div className="flex flex-wrap gap-2">
            {(recommendations.keywords_to_include || []).map((keyword: string, index: number) => (
              <span
                key={index}
                className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm"
              >
                {keyword}
              </span>
            ))}
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg border shadow-sm">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">
            🏆 Certifications to Pursue
          </h3>
          <ul className="space-y-2">
            {(recommendations.certifications_to_pursue || []).map(
              (cert: string, index: number) => (
                <li key={index} className="text-gray-700 flex items-start">
                  <span className="text-orange-500 mr-2">🎓</span>
                  {cert}
                </li>
              )
            )}
          </ul>
        </div>
      </div>
    </div>
  );
}