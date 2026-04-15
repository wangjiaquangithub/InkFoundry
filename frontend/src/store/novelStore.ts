import { create } from "zustand";
import type { Chapter, NovelProject, PipelineStatus, CharacterState } from "../types";
import { api } from "../api/client";

interface NovelStore {
  project: NovelProject | null;
  chapters: Chapter[];
  characters: CharacterState[];
  pipeline: PipelineStatus | null;
  selectedChapter: number | null;
  loading: boolean;
  error: string | null;

  // Actions
  fetchStatus: () => Promise<void>;
  fetchChapters: () => Promise<void>;
  fetchChapter: (num: number) => Promise<any>;
  fetchCharacters: () => Promise<void>;
  selectChapter: (num: number) => void;
  updateChapter: (num: number, content: string) => void;
  generateChapter: (num: number) => Promise<void>;
}

export const useNovelStore = create<NovelStore>((set, get) => ({
  project: null,
  chapters: [],
  characters: [],
  pipeline: null,
  selectedChapter: 1,
  loading: false,
  error: null,

  fetchStatus: async () => {
    set({ loading: true, error: null });
    try {
      const res = await api.status();
      set({ project: res.data });
    } catch (e) {
      set({ error: "Failed to fetch status" });
    } finally {
      set({ loading: false });
    }
  },

  fetchChapters: async () => {
    set({ loading: true });
    try {
      const res = await api.getChapters();
      set({ chapters: res.data.chapters || [] });
    } catch {
      set({ chapters: [] });
    } finally {
      set({ loading: false });
    }
  },

  fetchChapter: async (num: number) => {
    try {
      const res = await api.getChapter(num);
      return res.data;
    } catch (e: any) {
      set({ error: e.message });
      return null;
    }
  },

  fetchCharacters: async () => {
    try {
      const res = await api.getCharacters();
      const chars = res.data?.characters ?? [];
      set({ characters: Array.isArray(chars) ? chars : [] });
    } catch {
      set({ characters: [] });
    }
  },

  selectChapter: (num: number) => set({ selectedChapter: num }),

  updateChapter: async (num: number, content: string) => {
    try {
      await api.updateChapter(num, { content });
      // Refresh chapters
      get().fetchChapters();
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  generateChapter: async (num: number) => {
    set({ loading: true, error: null });
    try {
      await api.runChapter(num);
      // Refresh chapters after generation
      await get().fetchChapters();
    } catch (e: any) {
      set({ error: e.message });
    } finally {
      set({ loading: false });
    }
  },
}));
