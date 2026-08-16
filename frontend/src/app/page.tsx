"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { TopAppBar } from "@/components/TopAppBar";
import { SideNav } from "@/components/SideNav";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { endpoints } from "@/lib/api";
import { useStore } from "@/store/useStore";
import toast from "react-hot-toast";

export default function Home() {
  const router = useRouter();
  const [isUploading, setIsUploading] = useState(false);
  const [loadingStep, setLoadingStep] = useState<string>("");
  
  const { setGraphData, uploadId, incrementUploadId } = useStore();

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
        const pollInterval = setInterval(async () => {
          try {
            const statusRes = await fetch(endpoints.status(data.task_id));
            if (!statusRes.ok) throw new Error("Failed to get status");
            const statusData = await statusRes.json();

            setLoadingStep(statusData.message || "Processing...");

            if (statusData.status === "completed") {
              clearInterval(pollInterval);
              setGraphData(statusData.result);
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

  return (
    <>
      <TopAppBar />
      <div className="flex-1 flex overflow-hidden relative pt-14">
        <SideNav />
        <main className="flex-1 ml-16 flex flex-col md:flex-row h-full overflow-hidden">
          <ErrorBoundary sectionName="Upload Experience">
            <div className="flex-1 flex flex-col items-center justify-center bg-surface">
              <div className="p-8 border-2 border-dashed border-outline-variant rounded-xl flex flex-col items-center text-center bg-surface-bright max-w-[32rem] w-full shadow-sm">
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
          </ErrorBoundary>
        </main>
      </div>
    </>
  );
}
