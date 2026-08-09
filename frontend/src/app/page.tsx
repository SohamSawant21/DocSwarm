"use client";

import { useState } from "react";
import { TopAppBar } from "@/components/TopAppBar";
import { SideNav } from "@/components/SideNav";
import { FileTree } from "@/components/FileTree";
import { GraphCanvas } from "@/components/GraphCanvas";
import { RightPanel } from "@/components/RightPanel";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import type { UploadResponse } from "@/types";
import { endpoints } from "@/lib/api";

export default function Home() {
  const [graphData, setGraphData] = useState<UploadResponse | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadId, setUploadId] = useState<number>(0);
  const [loadingStep, setLoadingStep] = useState<string>("");

  const handleReset = () => {
    setGraphData(null);
    setSelectedNodeId(null);
    setUploadId((prev) => prev + 1);
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setLoadingStep("Uploading repository...");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(endpoints.upload, {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      
      if (!response.ok) {
        setIsUploading(false);
        setLoadingStep("");
        alert(data.detail || data.error || "Upload failed");
        return;
      }

      if (data.task_id) {
        // Poll for status
        const pollInterval = setInterval(async () => {
          try {
            const statusRes = await fetch(endpoints.status(data.task_id));
            if (!statusRes.ok) throw new Error("Failed to get status");
            const statusData = await statusRes.json();

            setLoadingStep(statusData.message || "Processing...");

            if (statusData.status === "completed") {
              clearInterval(pollInterval);
              setGraphData(statusData.result);
              setSelectedNodeId(null);
              setIsUploading(false);
              setLoadingStep("");
            } else if (statusData.status === "failed") {
              clearInterval(pollInterval);
              alert(statusData.error || "Processing failed");
              setIsUploading(false);
              setLoadingStep("");
            }
          } catch (err) {
            clearInterval(pollInterval);
            console.error("Polling error:", err);
            alert("Error checking status.");
            setIsUploading(false);
            setLoadingStep("");
          }
        }, 2000);
      } else {
        setIsUploading(false);
        setLoadingStep("");
        alert("No task ID returned");
      }
    } catch (error: any) {
      console.error("Error uploading file:", error);
      alert(error.message || "Error uploading file. Make sure backend is running.");
      setIsUploading(false);
      setLoadingStep("");
    }
  };

  return (
    <>
      <TopAppBar onReset={graphData ? handleReset : undefined} />
      <div className="flex-1 flex overflow-hidden relative pt-14">
        <SideNav />
        {/* Main Content Canvas */}
        <main className="flex-1 ml-16 flex flex-col md:flex-row h-full overflow-hidden">
          <ErrorBoundary sectionName="Application Engine" onReset={handleReset}>
            {!graphData ? (
            <div className="flex-1 flex flex-col items-center justify-center bg-surface">
              <div className=" p-8 border-2 border-dashed border-outline-variant rounded-xl flex flex-col items-center text-center bg-surface-bright">
                <span className="material-symbols-outlined text-[48px] text-outline mb-4">
                  upload_file
                </span>
                <h2 className="font-h2 text-h2 text-on-surface mb-2">
                  Upload Repository
                </h2>
                <p className="font-body-md text-on-surface-variant mb-6">
                  Select a .zip file containing your codebase to generate the
                  architecture graph.
                </p>
                <label className={`cursor-pointer bg-primary text-on-primary px-6 py-2 rounded-md font-ui-label text-ui-label transition-all duration-200 ${isUploading ? 'opacity-75 pointer-events-none' : 'hover:scale-[1.02] active:scale-[0.98] hover:bg-on-primary-fixed-variant'}`}>
                  {isUploading ? (
                    <div className="flex items-center gap-2">
                      <span className="material-symbols-outlined animate-spin text-[18px]">progress_activity</span>
                      {loadingStep}
                    </div>
                  ) : (
                    "Select .zip File"
                  )}
                  <input
                    key={uploadId}
                    type="file"
                    accept=".zip"
                    className="hidden"
                    onChange={handleFileUpload}
                    disabled={isUploading}
                  />
                </label>
              </div>
            </div>
          ) : (
            <>
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
                  />
                </ErrorBoundary>
              </div>
              <ErrorBoundary sectionName="Intelligence Panel">
                <RightPanel 
                  key={uploadId} 
                  sessionId={graphData.session_id}
                  selectedNodeId={selectedNodeId}
                  selectedNodeData={selectedNodeId && graphData ? graphData.files[selectedNodeId] : null}
                />
              </ErrorBoundary>
            </>
          )}
          </ErrorBoundary>
        </main>
      </div>
    </>
  );
}
