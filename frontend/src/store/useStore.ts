import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { UploadResponse } from '@/types';
import { endpoints } from '@/lib/api';

interface AppState {
  graphData: UploadResponse | null;
  selectedNodeId: string | null;
  activeFileContent: string | null;
  isFileLoading: boolean;
  uploadId: number;
  currentTaskId: string | null;
  isRestoring: boolean;

  setGraphData: (data: UploadResponse | null, taskId?: string) => void;
  setSelectedNodeId: (id: string | null) => void;
  reset: () => void;
  fetchFileContent: (sessionId: string, filepath: string) => Promise<void>;
  incrementUploadId: () => void;
  restoreSession: (taskId: string) => Promise<void>;
}

export const useStore = create<AppState>()(
  persist(
    (set, get) => ({
      graphData: null,
      selectedNodeId: null,
      activeFileContent: null,
      isFileLoading: false,
      uploadId: 0,
      currentTaskId: null,
      isRestoring: false,

      setGraphData: (data, taskId) => {
        set({ graphData: data });
        if (taskId) {
          set({ currentTaskId: taskId });
        }
      },
  
  setSelectedNodeId: (id) => {
    set({ selectedNodeId: id });
    const { graphData, fetchFileContent } = get();
    if (id && graphData?.session_id) {
      fetchFileContent(graphData.session_id, id);
    } else {
      set({ activeFileContent: null, isFileLoading: false });
    }
  },

  reset: () => set((state) => ({
    graphData: null,
    selectedNodeId: null,
    activeFileContent: null,
    isFileLoading: false,
    currentTaskId: null,
    isRestoring: false,
    uploadId: state.uploadId + 1
  })),
  
  incrementUploadId: () => set((state) => ({ uploadId: state.uploadId + 1 })),

  fetchFileContent: async (sessionId: string, filepath: string) => {
    set({ isFileLoading: true, activeFileContent: null });
    try {
      const res = await fetch(endpoints.fileContent(sessionId, filepath));
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        set({ activeFileContent: `Error: ${data.detail || "Unable to load file content"}` });
        return;
      }
      const data = await res.json();
      set({ activeFileContent: data.content });
    } catch (err: any) {
      if (err.name === 'AbortError') return;
      set({ activeFileContent: "Error: Could not connect to backend to fetch file." });
    } finally {
      set({ isFileLoading: false });
    }
  },

  restoreSession: async (taskId: string) => {
    set({ isRestoring: true });
    try {
      const res = await fetch(endpoints.status(taskId));
      if (!res.ok) throw new Error("Failed to get status");
      const statusData = await res.json();
      if (statusData.status === "completed" && statusData.result) {
        set({ graphData: statusData.result });
      } else {
        throw new Error("Session expired or not ready");
      }
    } catch (err) {
      set({ currentTaskId: null, graphData: null });
      throw err;
    } finally {
      set({ isRestoring: false });
    }
  }
    }),
    {
      name: 'docswarm-storage',
      partialize: (state) => ({ 
        uploadId: state.uploadId,
        currentTaskId: state.currentTaskId
      }),
    }
  )
);
