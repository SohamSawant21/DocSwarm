"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { TopAppBar } from "@/components/TopAppBar";
import { SideNav } from "@/components/SideNav";
import { FileTree } from "@/components/FileTree";
import { GraphCanvas } from "@/components/GraphCanvas";
import { RightPanel } from "@/components/RightPanel";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { useStore } from "@/store/useStore";
import toast from "react-hot-toast";

export default function Dashboard() {
  const router = useRouter();
  const {
    graphData,
    selectedNodeId,
    setSelectedNodeId,
    activeFileContent,
    isFileLoading,
    reset,
    uploadId,
    currentTaskId,
    isRestoring,
    restoreSession
  } = useStore();

  const [rightPanelWidth, setRightPanelWidth] = useState(400); // Default width
  const isDragging = useRef(false);

  const handleMouseMove = (e: MouseEvent) => {
    if (!isDragging.current) return;
    const newWidth = window.innerWidth - e.clientX;
    const maxWidth = Math.min(800, window.innerWidth - 300); // Leave at least 300px for main content
    if (newWidth >= 250 && newWidth <= maxWidth) {
      setRightPanelWidth(newWidth);
    }
  };

  const handleMouseUp = () => {
    isDragging.current = false;
    document.removeEventListener("mousemove", handleMouseMove);
    document.removeEventListener("mouseup", handleMouseUp);
    document.body.style.cursor = "default";
    document.body.style.userSelect = "auto";
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    isDragging.current = true;
    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  };

  useEffect(() => {
    if (!graphData) {
      if (currentTaskId && !isRestoring) {
        restoreSession(currentTaskId).catch(() => {
          toast.error("Session expired or missing. Please upload a repository.");
          router.replace("/");
        });
      } else if (!currentTaskId && !isRestoring) {
        toast.error("Session expired or missing. Please upload a repository.");
        router.replace("/");
      }
    }
  }, [graphData, currentTaskId, isRestoring, restoreSession, router]);

  const handleReset = () => {
    reset();
    router.replace("/");
  };

  if (isRestoring || !graphData) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-surface h-screen">
        <span className="material-symbols-outlined animate-spin text-[3rem] text-primary mb-4">progress_activity</span>
        <h2 className="font-h2 text-h2 text-on-surface">Restoring Session...</h2>
      </div>
    );
  }

  return (
    <>
      <TopAppBar onReset={handleReset} />
      <div className="flex-1 flex overflow-hidden relative pt-14">
        <SideNav />
        <main className="flex-1 ml-16 flex flex-col md:flex-row h-full overflow-hidden">
          <ErrorBoundary sectionName="Application Engine" onReset={handleReset}>
            {/* Left-Central Area with File Tree and DocGraph */}
            <div className="flex-1 flex overflow-hidden animate-fade-in">
              <ErrorBoundary sectionName="File Explorer">
                <FileTree 
                  data={graphData} 
                  selectedNodeId={selectedNodeId} 
                  onSelectNode={setSelectedNodeId} 
                />
              </ErrorBoundary>
              <ErrorBoundary sectionName="Graph Canvas">
                <GraphCanvas 
                  data={graphData} 
                  selectedNodeId={selectedNodeId} 
                  onSelectNode={setSelectedNodeId} 
                  activeFileContent={activeFileContent}
                  isFileLoading={isFileLoading}
                />
              </ErrorBoundary>
            </div>
            {/* Draggable Divider (Hidden on mobile) */}
            <div 
              onMouseDown={handleMouseDown}
              className="hidden md:block w-1 cursor-col-resize bg-surface-variant hover:bg-primary transition-colors flex-shrink-0 z-20"
              title="Drag to resize AI Chat panel"
            />
            <div 
              style={{ '--panel-width': `${rightPanelWidth}px` } as React.CSSProperties} 
              className="flex-shrink-0 h-full overflow-hidden flex flex-col border-l border-surface-variant bg-surface-bright w-full md:w-[var(--panel-width)]"
            >
              <ErrorBoundary sectionName="Intelligence Panel">
                <RightPanel 
                  key={uploadId} 
                  sessionId={graphData.session_id}
                  selectedNodeId={selectedNodeId}
                  selectedNodeData={selectedNodeId && graphData ? graphData.files[selectedNodeId] : null}
                  activeFileContent={activeFileContent}
                />
              </ErrorBoundary>
            </div>
          </ErrorBoundary>
        </main>
      </div>
    </>
  );
}
