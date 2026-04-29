"use client";

import { useState } from "react";
import { TopAppBar } from "@/components/TopAppBar";
import { SideNav } from "@/components/SideNav";
import { FileTree } from "@/components/FileTree";
import { GraphCanvas } from "@/components/GraphCanvas";
import { RightPanel } from "@/components/RightPanel";

export default function Home() {
  const [graphData, setGraphData] = useState<any>(null);
  const [isUploading, setIsUploading] = useState(false);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("http://localhost:8000/api/upload", {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      if (data.graph) {
        setGraphData(data);
      } else {
        alert(data.error || "Upload failed");
      }
    } catch (error) {
      console.error("Error uploading file:", error);
      alert("Error uploading file. Make sure backend is running.");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <>
      <TopAppBar />
      <div className="flex-1 flex overflow-hidden relative pt-14">
        <SideNav />
        {/* Main Content Canvas */}
        <main className="flex-1 ml-16 flex flex-col md:flex-row h-full overflow-hidden">
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
                <label className="cursor-pointer bg-primary text-on-primary px-6 py-2 rounded-md font-ui-label text-ui-label hover:bg-on-primary-fixed-variant transition-colors">
                  {isUploading ? "Parsing..." : "Select .zip File"}
                  <input
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
              <div className="flex-1 flex overflow-hidden">
                <FileTree data={graphData} />
                <GraphCanvas data={graphData} />
              </div>
              <RightPanel />
            </>
          )}
        </main>
      </div>
    </>
  );
}
