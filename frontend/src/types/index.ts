export interface CharacterState {
  name: string;
  role: string;
  status: string;
}

export interface WorldState {
  era: string;
  location: string;
  details: Record<string, string>;
}

export interface StateSnapshot {
  characters: CharacterState[];
  world: WorldState;
  version: number;
  timestamp: string;
}

export interface Chapter {
  chapter_num: number;
  number?: number;
  title: string;
  content: string;
  status: string;
  tension_level: number;
  word_count?: number;
  review_notes?: string;
  created_at?: string;
}

export interface NovelProject {
  id: string;
  title: string;
  genre: string;
  current_chapter: number;
  total_chapters: number;
  status: "idle" | "running" | "paused" | "completed" | "error";
}

export interface PipelineStatus {
  current_step: string;
  agent: string | null;
  progress: number;
  error: string | null;
}

// --- Phase 1+ types ---

export interface OutlineChapter {
  chapter_num: number;
  summary: string;
  tension: number;
}

export interface Outline {
  title: string;
  summary: string;
  total_chapters: number;
  arc: string;
  volume_plans: Array<{ volume: number; name: string; chapters: string }>;
  chapter_summaries: OutlineChapter[];
  tension_curve: number[];
  foreshadowing: Array<{ chapter: number; description: string }>;
  genre_rules: string[];
}

export interface CharacterProfile {
  name: string;
  gender: string;
  age: number;
  appearance: string;
  personality: string;
  backstory: string;
  motivation: string;
  voice_profile_ref: string;
}

export interface WorldBuilding {
  name: string;
  era: string;
  geography: string;
  social_structure: string;
  technology_level: string;
  cultures: Array<{ name: string; description: string }>;
  factions: Array<{ name: string; description: string }>;
}

export interface PipelineRunStatus {
  running: boolean;
  paused: boolean;
  current_chapter: number;
  total_chapters: number;
}

export interface ReviewItem {
  id: string;
  chapter_num: number;
  editor_score: number;
  issues: string[];
  redteam_issues: string[];
  status: "pending" | "approved" | "rejected";
}

export interface ProjectInfo {
  id: string;
  title: string;
  genre: string;
  summary: string;
  total_chapters: number;
  created_at: string;
  updated_at: string;
}
