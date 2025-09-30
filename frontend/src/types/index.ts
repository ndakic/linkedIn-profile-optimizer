export interface PersonalInfo {
  name: string | null;
  title: string | null;
  location: string | null;
  email: string | null;
  phone: string | null;
  linkedin_url: string | null;
}

export interface Experience {
  company: string;
  position: string;
  duration: string;
  location: string;
  responsibilities: string[];
}

export interface Education {
  institution: string;
  degree: string;
  field_of_study: string;
  graduation_year: string;
}

export interface Recommendation {
  recommender: string;
  relationship: string;
  content: string;
}

export interface ProfileData {
  personal_info: PersonalInfo;
  summary: string;
  experience: Experience[];
  education: Education[];
  skills: string[];
  certifications: string[];
  recommendations: Recommendation[];
  endorsements: string[];
  languages: string[];
  volunteer_experience: string[];
  publications_projects: string[];
}

export interface HeadlineRecommendation {
  current: string;
  suggested: string;
  reasoning: string;
}

export interface SummaryRecommendation {
  current: string;
  suggested: string;
  reasoning: string;
}

export interface ExperienceOptimization {
  company: string;
  position: string;
  current_description: string;
  suggested_description: string;
  reasoning: string;
}

export interface Recommendations {
  headline: HeadlineRecommendation;
  summary: SummaryRecommendation;
  experience_optimization: ExperienceOptimization[];
  skills_to_add: string[];
  skills_to_emphasize: string[];
  keywords_to_include: string[];
  certifications_to_pursue: string[];
}

export interface AnalysisResults {
  overall_score: number;
  strengths: string[];
  areas_for_improvement: string[];
  recommendations: Recommendations;
  industry_insights: string;
  next_steps: string[];
}

export interface ContentStrategy {
  posting_frequency: string;
  best_posting_times: string[];
  content_pillars: string[];
  hashtag_strategy: string[];
}

export interface ContentIdea {
  type: string;
  topic: string;
  objective: string;
  target_audience: string;
  content: string;
  hashtags: string[];
  call_to_action: string;
}

export interface SamplePost {
  title: string;
  content: string;
  hashtags: string[];
  engagement_hooks: string[];
}

export interface WeeklyCalendarItem {
  day: string;
  content_type: string;
  topic: string;
  brief_description: string;
}

export interface ContentResults {
  content_strategy: ContentStrategy;
  content_ideas: ContentIdea[];
  sample_posts: SamplePost[];
  weekly_content_calendar: WeeklyCalendarItem[];
}

export interface Summary {
  profile_completeness: number;
  optimization_score: number;
  key_improvements: string[];
  content_strategy: string[];
  recommended_actions: string[];
}

export interface OptimizationResults {
  success: boolean;
  status: string;
  profile_data?: ProfileData;
  analysis_results?: AnalysisResults;
  content_results?: ContentResults;
  summary?: Summary;
  error?: string;
  recommendations_count?: number;
  content_ideas_count?: number;
  sample_posts_count?: number;
}

export interface UploadState {
  isUploading: boolean;
  progress: number;
  status: string;
}