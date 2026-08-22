"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { TopAppBar } from "@/components/TopAppBar";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { endpoints } from "@/lib/api";
import { useStore } from "@/store/useStore";
import toast from "react-hot-toast";

export default function Home() {
  const router = useRouter();
  const [isUploading, setIsUploading] = useState(false);
  const [loadingStep, setLoadingStep] = useState<string>("");
  const [activeTab, setActiveTab] = useState<"zip" | "github">("zip");
  const [githubUrl, setGithubUrl] = useState("");
  
  const { setGraphData, uploadId, incrementUploadId } = useStore();

  const pollTaskStatus = (taskId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const statusRes = await fetch(endpoints.status(taskId));
        if (!statusRes.ok) throw new Error("Failed to get status");
        const statusData = await statusRes.json();

        setLoadingStep(statusData.message || "Processing...");

        if (statusData.status === "completed") {
          clearInterval(pollInterval);
          setGraphData(statusData.result, taskId);
          setIsUploading(false);
          setLoadingStep("");
          incrementUploadId();
          toast.success("Repository analyzed successfully!");
          router.push("/dashboard");
        } else if (statusData.status === "failed") {
          clearInterval(pollInterval);
          toast.error(statusData.error || "Processing failed");
          setIsUploading(false);
          setLoadingStep("");
        }
      } catch (err) {
        clearInterval(pollInterval);
        console.error("Polling error:", err);
        toast.error("Error checking status.");
        setIsUploading(false);
        setLoadingStep("");
      }
    }, 2000);
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
        toast.error(data.detail || data.error || "Upload failed");
        return;
      }

      if (data.task_id) {
        pollTaskStatus(data.task_id);
      } else {
        setIsUploading(false);
        setLoadingStep("");
        toast.error("No task ID returned");
      }
    } catch (error: any) {
      console.error("Error uploading file:", error);
      toast.error(error.message || "Error uploading file. Make sure backend is running.");
      setIsUploading(false);
      setLoadingStep("");
    }
  };

  const handleGithubImport = async (e: React.FormEvent) => {
    e.preventDefault();
    const url = githubUrl.trim();
    if (!url) {
      toast.error("Please enter a GitHub URL");
      return;
    }

    const githubRegex = /^https:\/\/github\.com\/[a-zA-Z0-9_-]+\/[a-zA-Z0-9_.-]+\/?$/;
    if (!githubRegex.test(url)) {
      toast.error("Please enter a valid GitHub repository URL (e.g., https://github.com/owner/repo)");
      return;
    }

    setIsUploading(true);
    setLoadingStep("Initializing GitHub import...");

    try {
      const response = await fetch(endpoints.importGithub, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      const data = await response.json();
      
      if (!response.ok) {
        setIsUploading(false);
        setLoadingStep("");
        toast.error(data.detail || data.error || "GitHub import failed");
        return;
      }

      if (data.task_id) {
        pollTaskStatus(data.task_id);
      } else {
        setIsUploading(false);
        setLoadingStep("");
        toast.error("No task ID returned");
      }
    } catch (error: any) {
      console.error("Error importing from GitHub:", error);
      toast.error(error.message || "Error importing from GitHub. Make sure backend is running.");
      setIsUploading(false);
      setLoadingStep("");
    }
  };

  return (
    <>
      <TopAppBar />
      <div className="flex-1 flex overflow-hidden relative pt-14">
        <main className="flex-1 flex flex-col md:flex-row h-full overflow-hidden">
          <ErrorBoundary sectionName="Upload Experience">
            <div className="flex-1 flex flex-col items-center justify-center bg-surface">
              <div className="p-8 border-2 border-dashed border-outline-variant rounded-xl flex flex-col items-center text-center bg-surface-bright max-w-[32rem] w-full shadow-sm">
                <span className="material-symbols-outlined text-[3rem] text-outline mb-4">
                  upload_file
                </span>
                <h2 className="font-h2 text-h2 text-on-surface mb-2">
                  Import Repository
                </h2>
                
                <div className="flex items-center justify-center bg-surface-container rounded-md p-1 mb-6 w-full max-w-xs mx-auto">
                  <button
                    onClick={() => setActiveTab('zip')}
                    disabled={isUploading}
                    className={`flex-1 flex justify-center items-center text-center px-4 py-1.5 rounded text-sm font-medium transition-colors ${activeTab === 'zip' ? 'bg-primary text-on-primary shadow-sm' : 'text-on-surface-variant hover:text-on-surface'}`}
                  >
                    Upload ZIP
                  </button>
                  <button
                    onClick={() => setActiveTab('github')}
                    disabled={isUploading}
                    className={`flex-1 flex justify-center items-center text-center px-4 py-1.5 rounded text-sm font-medium transition-colors ${activeTab === 'github' ? 'bg-primary text-on-primary shadow-sm' : 'text-on-surface-variant hover:text-on-surface'}`}
                  >
                    GitHub URL
                  </button>
                </div>

                {activeTab === 'zip' ? (
                  <>
                    <p className="font-body-md text-on-surface-variant mb-6">
                      Select a .zip file containing your codebase to generate the
                      architecture graph.
                    </p>
                    <label className={`cursor-pointer bg-primary text-on-primary px-6 py-2 rounded-md font-ui-label text-ui-label transition-all duration-200 ${isUploading ? 'opacity-75 pointer-events-none' : 'hover:scale-[1.02] active:scale-[0.98] hover:bg-on-primary-fixed-variant'}`}>
                      {isUploading ? (
                        <div className="flex items-center gap-2">
                          <span className="material-symbols-outlined animate-spin text-[1.1250rem]">progress_activity</span>
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
                  </>
                ) : (
                  <>
                    <p className="font-body-md text-on-surface-variant mb-6">
                      Paste a public GitHub repository URL to import it directly.
                    </p>
                    <form onSubmit={handleGithubImport} className="flex flex-col w-full gap-4 items-center">
                      <input 
                        type="url" 
                        placeholder="https://github.com/owner/repository" 
                        value={githubUrl}
                        onChange={(e) => setGithubUrl(e.target.value)}
                        disabled={isUploading}
                        required
                        className="w-full px-4 py-2 border border-outline-variant rounded-md bg-surface text-on-surface focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                      />
                      <button 
                        type="submit" 
                        disabled={isUploading || !githubUrl.trim()}
                        className={`bg-primary text-on-primary px-6 py-2 rounded-md font-ui-label text-ui-label transition-all duration-200 ${(isUploading || !githubUrl.trim()) ? 'opacity-75 pointer-events-none' : 'hover:scale-[1.02] active:scale-[0.98] hover:bg-on-primary-fixed-variant'}`}
                      >
                        {isUploading ? (
                          <div className="flex items-center gap-2">
                            <span className="material-symbols-outlined animate-spin text-[1.1250rem]">progress_activity</span>
                            {loadingStep}
                          </div>
                        ) : (
                          "Import from GitHub"
                        )}
                      </button>
                    </form>
                  </>
                )}
              </div>
            </div>
          </ErrorBoundary>
        </main>
      </div>
    </>
  );
}
