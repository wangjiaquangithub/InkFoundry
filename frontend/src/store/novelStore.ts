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
  fetchCharacters: () => Promise<void>;
  selectChapter: (num: number) => void;
  updateChapter: (num: number, content: string) => void;
}

export const useNovelStore = create<NovelStore>((set, get) => ({
  project: null,
  chapters: [],
  characters: [],
  pipeline: null,
  selectedChapter: null,
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

  fetchCharacters: async () => {
    try {
      const res = await api.getCharacters();
      set({ characters: res.data });
    } catch {
      set({ error: "Failed to fetch characters" });
    }
  },

  selectChapter: (num: number) => set({ selectedChapter: num }),

  updateChapter: (num: number, content: string) => {
    const chapters = get().chapters.map((c) =>
      c.number === num ? { ...c, content } : c
    );
    set({ chapters });
  },
}));
