"use client";

import { useState } from "react";
import type { UploadResponse } from "@/types";
import { FileNode } from "./FileNode";

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

  if (!data || !data.file_tree) return null;

  return (
    <div className="w-64 bg-surface-bright border-r border-outline-variant flex flex-col shrink-0 overflow-hidden">
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
      <div className="flex-1 overflow-y-auto px-4 pb-6">
        <div className="font-body-md text-[14px]">
          {data.file_tree.length === 0 ? (
            <p className="text-outline text-[13px] py-2 px-2">No files found.</p>
          ) : (
            data.file_tree.map((node, index) => (
              <FileNode
                key={`${node.path || node.name}-${index}`}
                node={node}
                level={0}
                selectedNodeId={selectedNodeId}
                onSelectNode={onSelectNode}
                searchQuery={query}
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
}
