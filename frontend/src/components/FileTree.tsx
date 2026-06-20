"use client";

import { useState } from "react";
import type { UploadResponse, FileData } from "@/types";

export function FileTree({ 
  data,
  selectedNodeId,
  onSelectNode
}: { 
  data: UploadResponse;
  selectedNodeId: string | null;
  onSelectNode: (id: string | null) => void;
}) {
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState("");

  if (!data || !data.files) return null;

  const entries = Object.entries(data.files) as [string, FileData][];
  const filtered = query.trim()
    ? entries.filter(([path, file]) =>
        file.label.toLowerCase().includes(query.toLowerCase()) ||
        path.toLowerCase().includes(query.toLowerCase())
      )
    : entries;

  return (
    <div className="w-64 bg-[#F8F8F6] border-r border-[#E5E5E1] flex flex-col shrink-0 overflow-hidden">
      {/* Header row */}
      <div className="px-6 pt-6 pb-3 flex items-center justify-between">
        {searchOpen ? (
          <div className="flex items-center gap-2 w-full">
            <span className="material-symbols-outlined text-[16px] text-outline shrink-0">
              search
            </span>
            <input
              autoFocus
              className="flex-1 bg-transparent border-none outline-none text-[13px] text-on-surface placeholder:text-outline font-body-md"
              placeholder="Search files..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <button
              onClick={() => { setSearchOpen(false); setQuery(""); }}
              className="text-outline hover:text-on-surface transition-colors"
            >
              <span className="material-symbols-outlined text-[16px]">close</span>
            </button>
          </div>
        ) : (
          <>
            <h4 className="font-ui-label text-[12px] uppercase tracking-[0.1em] text-outline">
              Workspace
            </h4>
            <button
              onClick={() => setSearchOpen(true)}
              className="text-outline hover:text-on-surface transition-colors p-0.5 rounded"
              title="Search files"
            >
              <span className="material-symbols-outlined text-[16px]">search</span>
            </button>
          </>
        )}
      </div>

      {/* File list */}
      <div className="flex-1 overflow-y-auto px-6 pb-6">
        <div className="space-y-1 font-file-tree text-[14px]">
          {filtered.length === 0 ? (
            <p className="text-outline text-[13px] py-2">No files match.</p>
          ) : (
            filtered.map(([path, file]) => {
              const isSelected = path === selectedNodeId;
              return (
                <div
                  key={path}
                  onClick={() => onSelectNode(isSelected ? null : path)}
                  className={`flex items-center gap-3 cursor-pointer py-1.5 rounded px-1 group transition-colors ${
                    isSelected 
                      ? "bg-primary text-on-primary hover:bg-primary-fixed hover:text-on-primary-fixed" 
                      : "text-on-surface-variant hover:text-on-surface hover:bg-[#EFEFED]"
                  }`}
                >
                  <span className={`material-symbols-outlined text-[16px] transition-colors shrink-0 ${
                    isSelected ? "text-on-primary" : "text-outline group-hover:text-primary"
                  }`}>
                    {file.icon || "description"}
                  </span>
                  <span className="truncate" title={path}>
                    {file.label}
                  </span>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
