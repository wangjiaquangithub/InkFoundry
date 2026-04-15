import { create } from "zustand";
import { api } from "../api/client";

interface ProjectState {
  title: string;
  genre: string;
  summary: string;
  totalChapters: number;
  currentChapter: number;
  loading: boolean;

  // Actions
  setTitle: (title: string) => void;
  setGenre: (genre: string) => void;
  setSummary: (summary: string) => void;
  setTotalChapters: (total: number) => void;
  setCurrentChapter: (num: number) => void;
  generateOutline: () => Promise<any>;
  loadFromPending: () => void;
  reset: () => void;
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  title: "",
  genre: "xuanhuan",
  summary: "",
  totalChapters: 100,
  currentChapter: 1,
  loading: false,

  setTitle: (title: string) => set({ title }),
  setGenre: (genre: string) => set({ genre }),
  setSummary: (summary: string) => set({ summary }),
  setTotalChapters: (total: number) => set({ totalChapters: total }),
  setCurrentChapter: (num: number) => set({ currentChapter: num }),

  generateOutline: async () => {
    set({ loading: true });
    try {
      const state = get();
      const res = await api.generateOutline({
        genre: state.genre,
        title: state.title || "未命名",
        summary: state.summary,
        total_chapters: state.totalChapters,
      });
      set({ loading: false });
      return res.data;
    } catch (e: any) {
      set({ loading: false });
      throw e;
    }
  },

  loadFromPending: () => {
    const pending = localStorage.getItem("pendingProject");
    if (pending) {
      const data = JSON.parse(pending);
      set({
        title: data.title || "",
        genre: data.genre || "xuanhuan",
        summary: data.summary || "",
        totalChapters: data.totalChapters || 100,
      });
    }
  },

  reset: () => {
    set({
      title: "",
      genre: "xuanhuan",
      summary: "",
      totalChapters: 100,
      currentChapter: 1,
      loading: false,
    });
  },
}));
