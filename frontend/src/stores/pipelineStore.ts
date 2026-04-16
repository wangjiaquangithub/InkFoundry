import { create } from "zustand";
import type { PipelineRunStatus } from "../types";
import { api } from "../api/client";

const getErrorMessage = (error: unknown) =>
  error instanceof Error ? error.message : "Unknown error";

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
  runChapter: (num: number) => Promise<unknown>;
  runBatch: (start: number, end: number) => Promise<unknown>;
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
      const data = res.data as Partial<PipelineRunStatus>;
      set({
        running: data.running || false,
        paused: data.paused || false,
        currentChapter: data.current_chapter || 0,
        totalChapters: data.total_chapters || 0,
        error: null,
      });
    } catch (error: unknown) {
      set({ error: getErrorMessage(error) });
    }
  },

  runChapter: async (num: number) => {
    set({ loading: true, error: null });
    try {
      const res = await api.runChapter(num);
      set({ loading: false, currentChapter: num, running: true, progress: 0 });
      return res.data as unknown;
    } catch (error: unknown) {
      const normalizedError = error instanceof Error ? error : new Error(getErrorMessage(error));
      set({ loading: false, error: normalizedError.message });
      throw normalizedError;
    }
  },

  runBatch: async (start: number, end: number) => {
    set({ loading: true, error: null });
    try {
      const res = await api.runBatch({ start_chapter: start, end_chapter: end });
      set({ loading: false, running: true, currentChapter: start, totalChapters: end - start + 1 });
      return res.data as unknown;
    } catch (error: unknown) {
      const normalizedError = error instanceof Error ? error : new Error(getErrorMessage(error));
      set({ loading: false, error: normalizedError.message });
      throw normalizedError;
    }
  },

  pause: async () => {
    try {
      await api.pausePipeline();
      set({ paused: true });
    } catch (error: unknown) {
      set({ error: getErrorMessage(error) });
    }
  },

  resume: async () => {
    try {
      await api.resumePipeline();
      set({ paused: false });
    } catch (error: unknown) {
      set({ error: getErrorMessage(error) });
    }
  },

  stop: async () => {
    try {
      await api.stopPipeline();
      set({ running: false, paused: false, currentStep: "", progress: 0 });
    } catch (error: unknown) {
      set({ error: getErrorMessage(error) });
    }
  },

  setError: (error: string | null) => {
    set({ error });
  },
}));
