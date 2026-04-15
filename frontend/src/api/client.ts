import axios from "axios";
import type { Outline, CharacterProfile, WorldBuilding } from "../types";

const API_BASE = "";

const client = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

export const api = {
  health: () => client.get("/health"),
  status: () => client.get("/api/status"),

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
    client.post("/api/outlines/generate", data),
  updateOutline: (data: Partial<Outline>) =>
    client.put("/api/outlines", data),

  // Pipeline
  runChapter: (num: number) => client.post(`/api/pipeline/run-chapter/${num}`),
  runBatch: (data: { start_chapter: number; end_chapter: number }) =>
    client.post("/api/pipeline/run-batch", data),
  getPipelineStatus: () => client.get("/api/pipeline/status"),
  pausePipeline: () => client.post("/api/pipeline/pause"),
  resumePipeline: () => client.post("/api/pipeline/resume"),
  stopPipeline: () => client.post("/api/pipeline/stop"),

  // Configuration
  getConfig: () => client.get("/api/config"),
  saveConfig: (data: Record<string, any>) => client.post("/api/config", data),

  // State
  getStateSnapshot: () => client.get("/api/state/snapshot"),
};

export default api;
