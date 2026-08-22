"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { TopAppBar } from "@/components/TopAppBar";
import { SideNav } from "@/components/SideNav";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { useStore } from "@/store/useStore";
import toast from "react-hot-toast";
import { Terminal, Copy, Check } from "lucide-react";

export default function Clipage() {
  const router = useRouter();
  const { graphData, reset, currentTaskId, isRestoring, restoreSession } = useStore();
  const [copied, setCopied] = useState(false);

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

  const installCommand = "curl -sL https://docswarm.dev/install.sh | bash"; // Placeholder command

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(installCommand);
      setCopied(true);
      toast.success("Command copied to clipboard!");
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
      toast.error("Failed to copy command.");
    }
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
        <main className="flex-1 ml-16 overflow-y-auto bg-surface-container p-8">
          <ErrorBoundary sectionName="CLI Dashboard" onReset={handleReset}>
            <div className="max-w-4xl mx-auto pb-20">
              <div className="mb-8">
                <div className="flex items-center gap-3 mb-2">
                  <Terminal className="text-primary" size={32} />
                  <h1 className="text-3xl font-display font-bold text-on-surface">CLI / Offline</h1>
                </div>
                <p className="text-on-surface-variant text-lg">
                  Run the same application locally through the CLI and use it without requiring an online connection.
                </p>
              </div>
              
              <div className="bg-surface rounded-xl border border-outline-variant shadow-sm overflow-hidden mb-8">
                <div className="p-6 border-b border-outline-variant bg-surface-bright">
                  <h2 className="text-xl font-bold text-on-surface">Install the CLI</h2>
                  <p className="text-sm text-on-surface-variant mt-1">
                    Run the following command in your terminal to install the DocSwarm CLI globally on your machine.
                  </p>
                </div>
                
                <div className="p-6">
                  <div className="relative group">
                    <div className="flex items-center bg-[#1e1e1e] rounded-lg p-4 font-code text-sm text-[#d4d4d4] overflow-x-auto">
                      <span className="select-none text-[#569cd6] mr-4">$</span>
                      <code className="whitespace-pre">{installCommand}</code>
                    </div>
                    <button
                      onClick={handleCopy}
                      className="absolute right-3 top-1/2 -translate-y-1/2 p-2 bg-surface/10 hover:bg-surface/20 text-[#d4d4d4] rounded-md transition-all backdrop-blur-sm"
                      title="Copy to clipboard"
                    >
                      {copied ? <Check size={18} className="text-green-400" /> : <Copy size={18} />}
                    </button>
                  </div>
                </div>
              </div>

              <div className="bg-surface-bright p-6 rounded-xl border border-outline-variant shadow-sm">
                <h3 className="text-lg font-semibold text-on-surface mb-2">Why use the CLI?</h3>
                <ul className="space-y-3 text-on-surface-variant list-disc list-inside">
                  <li><strong>Total Privacy:</strong> Analyze your repositories locally without uploading any code to external servers.</li>
                  <li><strong>Offline Mode:</strong> Work anywhere, even without an active internet connection.</li>
                  <li><strong>CI/CD Integration:</strong> Seamlessly integrate DocSwarm into your automated pipelines.</li>
                  <li><strong>Performance:</strong> Faster analysis for large enterprise codebases directly on your machine hardware.</li>
                </ul>
              </div>
            </div>
          </ErrorBoundary>
        </main>
      </div>
    </>
  );
}
