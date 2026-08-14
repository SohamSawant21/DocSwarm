"use client";

import { useEffect } from "react";
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
    uploadId
  } = useStore();

  useEffect(() => {
    if (!graphData) {
      toast.error("Session expired or missing. Please upload a repository.");
      router.replace("/");
    }
  }, [graphData, router]);

  const handleReset = () => {
    reset();
    router.replace("/");
  };

  if (!graphData) {
    return null; // Will redirect
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
            <ErrorBoundary sectionName="Intelligence Panel">
              <RightPanel 
                key={uploadId} 
                sessionId={graphData.session_id}
                selectedNodeId={selectedNodeId}
                selectedNodeData={selectedNodeId && graphData ? graphData.files[selectedNodeId] : null}
                activeFileContent={activeFileContent}
              />
            </ErrorBoundary>
          </ErrorBoundary>
        </main>
      </div>
    </>
  );
}
