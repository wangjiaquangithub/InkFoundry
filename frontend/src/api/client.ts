import axios from "axios";
import type { Outline, CharacterProfile, WorldBuilding, NovelProject } from "../types";

export interface ProjectRecord {
  id: string;
  title: string;
  genre: string;
  summary: string;
  target_chapters: number;
  created_at: string;
  last_modified: string;
  status: string;
  total_chapters?: number;
  latest_chapter?: number;
  outline_total_chapters?: number;
}

export interface OutlineGenerateResponse {
  message: string;
  outline: Outline;
  mode: "model" | "fallback";
}

export interface ChapterRunResponse {
  chapter_num: number;
  status: string;
  error?: string;
  detail?: string;
  mode?: "model" | "fallback";
}

export interface ApiStatusResponse {
  id: string;
  title: string;
  genre: string;
  current_chapter: number;
  total_chapters: number;
  status: NovelProject["status"];
}

export interface SnapshotRecord {
  version: number;
  chapter_num: number;
  characters: Array<{ name: string; role: string; status: string }>;
  world_states: Array<{ name: string; description: string; state: string }>;
  summary: string;
  metadata: {
    chapters?: Array<{
      chapter_num: number;
      title: string;
      content: string;
      status: string;
      word_count: number;
      tension_level: number;
      version: number;
      review_notes: string;
      agent_results: Record<string, unknown> | string;
      created_at: string;
      updated_at: string;
    }>;
    [key: string]: unknown;
  };
}

const API_BASE = "";

const client = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

export const api = {
  health: () => client.get("/health"),
  status: () => client.get<ApiStatusResponse>("/api/status"),

  // Chapters
  getChapters: () => client.get("/api/chapters"),
  getChapter: (num: number) => client.get(`/api/chapters/${num}`),
  createChapter: (data: { title?: string; content?: string }) =>
    client.post("/api/chapters", data),
  updateChapter: (num: number, data: Partial<{ title: string; content: string; status: string }>) =>
    client.put(`/api/chapters/${num}`, data),
  deleteChapter: (num: number) => client.delete(`/api/chapters/${num}`),

  // Characters
  getCharacters: () => client.get("/api/characters"),
  createCharacter: (data: { name: string; role?: string; status?: string }) =>
    client.post("/api/characters", data),
  getCharacter: (name: string) => client.get(`/api/characters/${name}`),
  updateCharacter: (name: string, data: { role?: string; status?: string }) =>
    client.put(`/api/characters/${name}`, data),
  deleteCharacter: (name: string) => client.delete(`/api/characters/${name}`),

  // Profiles
  getProfiles: () => client.get("/api/profiles"),
  createProfile: (data: Partial<CharacterProfile>) =>
    client.post("/api/profiles", data),
  updateProfile: (name: string, data: Partial<CharacterProfile>) =>
    client.put(`/api/profiles/${name}`, data),
  deleteProfile: (name: string) => client.delete(`/api/profiles/${name}`),

  // Relationships
  getRelationships: () => client.get("/api/relationships"),
  createRelationship: (data: { from_character: string; to_character: string; relationship_type: string; strength?: number }) =>
    client.post("/api/relationships", data),

  // World Building
  getWorldBuilding: () => client.get("/api/world-building"),
  createWorldBuilding: (data: Partial<WorldBuilding>) =>
    client.post("/api/world-building", data),

  // Outlines
  getOutline: () => client.get("/api/outlines"),
  generateOutline: (data: { genre?: string; title?: string; summary?: string; total_chapters?: number }) =>
    client.post<OutlineGenerateResponse>("/api/outlines/generate", data),
  updateOutline: (data: Partial<Outline>) =>
    client.put("/api/outlines", data),

  // Pipeline
  runChapter: (num: number) => client.post<ChapterRunResponse>(`/api/pipeline/run-chapter/${num}`),
  runBatch: (data: { start_chapter: number; end_chapter: number }) =>
    client.post("/api/pipeline/run-batch", data),
  getPipelineStatus: () => client.get("/api/pipeline/status"),
  pausePipeline: () => client.post("/api/pipeline/pause"),
  resumePipeline: () => client.post("/api/pipeline/resume"),
  stopPipeline: () => client.post("/api/pipeline/stop"),

  // Configuration
  getConfig: () => client.get("/api/config"),
  saveConfig: (data: Record<string, unknown>) => client.post("/api/config", data),
  resetConfig: () => client.delete("/api/config"),

  // Power Systems
  getPowerSystems: () => client.get("/api/power-systems"),
  createPowerSystem: (data: { name: string; levels: string[]; rules: string }) =>
    client.post("/api/power-systems", data),

  // Timeline
  getTimeline: () => client.get("/api/timeline"),
  createTimelineEvent: (data: { year: number; event: string; impact: string }) =>
    client.post("/api/timeline", data),

  // Review
  approveChapter: (num: number) => client.post(`/api/review/approve/${num}`),
  rejectChapter: (num: number, note: string) =>
    client.post(`/api/review/reject/${num}`, { note }),

  // State
  getStateSnapshot: () => client.get("/api/state/snapshot"),

  // Export
  exportNovel: (format: string) =>
    client.post("/api/export", { format }),

  // Projects
  listProjects: () => client.get<{ projects: ProjectRecord[] }>("/api/projects"),
  createProject: (data: { title: string; genre?: string; summary: string; target_chapters?: number }) =>
    client.post<{ message: string; project: ProjectRecord }>("/api/projects", data),
  getActiveProject: () => client.get<{ project: ProjectRecord | null }>("/api/projects/active"),
  getProject: (id: string) => client.get<{ project: ProjectRecord }>(`/api/projects/${id}`),
  deleteProject: (id: string) => client.delete(`/api/projects/${id}`),
  activateProject: (id: string) => client.post(`/api/projects/${id}/activate`),

  // Token Stats
  getTokenStats: () => client.get("/api/token-stats"),
  getTokenRecords: () => client.get("/api/token-records"),

  // Snapshots
  saveSnapshot: () => client.post<{ message: string; version: number }>("/api/snapshots"),
  listSnapshots: () => client.get<{ snapshots: SnapshotRecord[] }>("/api/snapshots"),
  restoreSnapshot: (version: number) => client.post<{ message: string }>(`/api/snapshots/${version}/restore`),
  deleteSnapshot: (version: number) => client.delete<{ message: string }>(`/api/snapshots/${version}`),

  // Phase 3: Value-Add Features
  // Daemon
  getDaemonStatus: () => client.get("/api/daemon/status"),
  startDaemon: (data: { start_chapter?: number; end_chapter?: number; interval_seconds?: number }) =>
    client.post("/api/daemon/start", data),
  stopDaemon: () => client.post("/api/daemon/stop"),

  // Import
  importText: (data: { title: string; content: string }) =>
    client.post("/api/import/text", data),
  importAndApply: (data: { title: string; content: string }) =>
    client.post("/api/import/apply", data),

  // Side Story
  generateSideStory: (data: { characters?: string[]; setting?: string; topic?: string }) =>
    client.post("/api/side-story/generate", data),

  // Imitation
  generateImitation: (data: { sample_text: string; topic: string }) =>
    client.post("/api/imitation/generate", data),

  // Style
  extractStyle: (text: string) =>
    client.post("/api/style/extract", { text }),
  getStyleFingerprint: (text: string) =>
    client.post("/api/style/fingerprint", { text }),

  // AI Detection
  aiDetect: (text: string) =>
    client.post("/api/ai-detect", { text }),

  // Trend Analysis
  analyzeTrends: (data: { genre?: string; keywords?: string[] }) =>
    client.post("/api/trends/analyze", data),
};

export default api;
