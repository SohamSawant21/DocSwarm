"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { TopAppBar } from "@/components/TopAppBar";
import { SideNav } from "@/components/SideNav";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { useStore } from "@/store/useStore";
import { endpoints } from "@/lib/api";
import toast from "react-hot-toast";
import { MarkdownViewer } from "@/components/MarkdownViewer";

export default function DocsPage() {
  const router = useRouter();
  const { graphData, reset } = useStore();
  const [docsContent, setDocsContent] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const isGeneratingRef = useRef<boolean>(false);
  const initializedRef = useRef<boolean>(false);

  // Auto-fetch docs once on mount
  useEffect(() => {
    if (!graphData) {
      toast.error("Session expired or missing. Please upload a repository.");
      router.replace("/");
    } else {
      if (!initializedRef.current) {
        initializedRef.current = true;
        generateDocs();
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleReset = () => {
    reset();
    router.replace("/");
  };

  const generateDocs = async () => {
    if (!graphData?.session_id) return;
    if (isGeneratingRef.current) return;
    
    setIsGenerating(true);
    isGeneratingRef.current = true;
    setDocsContent(null);
    try {
      const response = await fetch(endpoints.generateDocs, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: graphData.session_id }),
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        toast.error(data.detail || "Failed to generate documentation");
        return;
      }
      
      setDocsContent(data.docs);
      toast.success("Documentation generated successfully!");
    } catch (err: any) {
      toast.error("An error occurred while generating documentation.");
      console.error(err);
    } finally {
      setIsGenerating(false);
      isGeneratingRef.current = false;
    }
  };

  const handleDownload = () => {
    if (!docsContent) {
      toast.error("No documentation available to download.");
      return;
    }
    
    try {
      const blob = new Blob([docsContent], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "README.md";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success("Downloaded README.md successfully!");
    } catch (err) {
      console.error("Failed to download documentation:", err);
      toast.error("Failed to download documentation.");
    }
  };

  if (!graphData) {
    return null; // Will redirect
  }

  return (
    <>
      <TopAppBar onReset={handleReset} />
      <div className="flex-1 flex overflow-hidden relative pt-14">
        <SideNav />
        <main className="flex-1 ml-16 flex flex-col h-full overflow-hidden bg-surface">
          <ErrorBoundary sectionName="AI Docs Engine" onReset={handleReset}>
            <div className="w-full max-w-5xl mx-auto p-8 h-full flex flex-col">
              <div className="flex justify-between items-center mb-8 shrink-0">
                <div>
                  <h1 className="text-3xl font-display font-bold text-on-surface">Repository Documentation</h1>
                  <p className="text-on-surface-variant mt-2">AI-generated architecture and API reference</p>
                </div>
                <div className="flex items-center gap-3">
                  {docsContent && (
                    <button
                      onClick={handleDownload}
                      className="bg-surface-container-high text-on-surface px-6 py-2.5 rounded-md font-ui-label text-ui-label transition-all duration-200 flex items-center gap-2 shadow-sm border border-outline-variant hover:scale-[1.02] active:scale-[0.98] hover:bg-surface-container-highest"
                    >
                      <span className="material-symbols-outlined text-[1.1250rem]">download</span>
                      Download README.md
                    </button>
                  )}
                  <button
                    onClick={generateDocs}
                    disabled={isGenerating}
                    className={`bg-primary text-on-primary px-6 py-2.5 rounded-md font-ui-label text-ui-label transition-all duration-200 flex items-center gap-2 shadow-sm
                      ${isGenerating ? 'opacity-70 cursor-not-allowed' : 'hover:scale-[1.02] active:scale-[0.98] hover:bg-on-primary-fixed-variant'}`}
                  >
                    <span className={`material-symbols-outlined text-[1.1250rem] ${isGenerating ? 'animate-spin' : ''}`}>
                      {isGenerating ? 'progress_activity' : 'auto_awesome'}
                    </span>
                    {isGenerating ? 'Generating...' : (docsContent ? 'Regenerate Docs' : 'Generate Docs')}
                  </button>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto bg-surface-bright rounded-xl border border-outline-variant shadow-sm p-8 markdown-body">
                {!docsContent && !isGenerating && (
                  <div className="h-full flex flex-col items-center justify-center text-on-surface-variant opacity-70">
                    <span className="material-symbols-outlined text-[4rem] mb-4">description</span>
                    <p>Click "Generate Docs" to create documentation for your repository.</p>
                  </div>
                )}
                
                {isGenerating && !docsContent && (
                  <div className="h-full flex flex-col items-center justify-center text-primary animate-pulse">
                    <span className="material-symbols-outlined text-[4rem] mb-4 animate-spin">progress_activity</span>
                    <p className="text-on-surface">Analyzing repository and generating documentation...</p>
                    <p className="text-on-surface-variant text-sm mt-2 text-center">This may take a moment depending on the size of your project.</p>
                  </div>
                )}

                {docsContent && (
                  <div className="prose prose-slate max-w-none prose-headings:font-display prose-a:text-primary">
                    <MarkdownViewer content={docsContent} />
                  </div>
                )}
              </div>
            </div>
          </ErrorBoundary>
        </main>
      </div>
    </>
  );
}
