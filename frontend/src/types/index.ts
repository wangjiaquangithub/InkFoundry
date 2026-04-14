export interface CharacterState {
  name: string;
  status: string;
  traits: string[];
  description: string;
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
  number: number;
  content: string;
  status: "pending" | "draft" | "reviewed" | "final";
  tension_level: number;
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
