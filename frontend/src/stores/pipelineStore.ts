import { create } from "zustand";
import { api } from "../api/client";

interface PipelineState {
  running: boolean;
  paused: boolean;
  currentChapter: number;
  totalChapters: number;
  currentStep: string;
  currentAgent: string;
  progress: number;
  error: string | null;
  loading: boolean;

  // Actions
  fetchStatus: () => Promise<void>;
  runChapter: (num: number) => Promise<any>;
  runBatch: (start: number, end: number) => Promise<any>;
  pause: () => Promise<void>;
  resume: () => Promise<void>;
  stop: () => Promise<void>;
  setError: (error: string | null) => void;
}

export const usePipelineStore = create<PipelineState>((set) => ({
  running: false,
  paused: false,
  currentChapter: 0,
  totalChapters: 0,
  currentStep: "",
  currentAgent: "",
  progress: 0,
  error: null,
  loading: false,

  fetchStatus: async () => {
    try {
      const res = await api.getPipelineStatus();
      const data = res.data;
      set({
        running: data.running || false,
        paused: data.paused || false,
        currentChapter: data.current_chapter || 0,
        totalChapters: data.total_chapters || 0,
      });
    } catch {
      // Silently fail
    }
  },

  runChapter: async (num: number) => {
    set({ loading: true, error: null });
    try {
      const res = await api.runChapter(num);
      set({ loading: false, currentChapter: num, running: true, progress: 0 });
      return res.data;
    } catch (e: any) {
      set({ loading: false, error: e.message });
      throw e;
    }
  },

  runBatch: async (start: number, end: number) => {
    set({ loading: true, error: null });
    try {
      const res = await api.runBatch({ start_chapter: start, end_chapter: end });
      set({ loading: false, running: true, currentChapter: start, totalChapters: end - start + 1 });
      return res.data;
    } catch (e: any) {
      set({ loading: false, error: e.message });
      throw e;
    }
  },

  pause: async () => {
    set({ paused: true });
  },

  resume: async () => {
    set({ paused: false });
  },

  stop: async () => {
    set({ running: false, paused: false, currentStep: "", progress: 0 });
  },

  setError: (error: string | null) => {
    set({ error });
  },
}));
