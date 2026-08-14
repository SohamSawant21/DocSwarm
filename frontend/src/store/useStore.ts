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

  setGraphData: (data: UploadResponse | null) => void;
  setSelectedNodeId: (id: string | null) => void;
  reset: () => void;
  fetchFileContent: (sessionId: string, filepath: string) => Promise<void>;
  incrementUploadId: () => void;
}

export const useStore = create<AppState>()(
  persist(
    (set, get) => ({
      graphData: null,
      selectedNodeId: null,
      activeFileContent: null,
      isFileLoading: false,
      uploadId: 0,

      setGraphData: (data) => set({ graphData: data }),
  
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
  }
    }),
    {
      name: 'docswarm-storage',
      partialize: (state) => ({ 
        graphData: state.graphData,
        uploadId: state.uploadId
      }),
    }
  )
);
