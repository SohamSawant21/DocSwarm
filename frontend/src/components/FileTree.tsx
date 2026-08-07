"use client";

import { useState, useDeferredValue, useRef, useEffect, useMemo, useCallback } from "react";
import type { UploadResponse } from "@/types";
import { Virtuoso, VirtuosoHandle } from "react-virtuoso";
import { FileNodeRow } from "./FileNode";
import { useFileTree } from "@/hooks/useFileTree";

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
  const deferredQuery = useDeferredValue(query);

  const virtuosoRef = useRef<VirtuosoHandle>(null);
  
  const { flatList, expandedFolders, toggleFolder, expandAll, collapseAll } = useFileTree(
    data?.file_tree || [],
    selectedNodeId,
    deferredQuery
  );

  // Sync scroll with selected node
  useEffect(() => {
    if (selectedNodeId && flatList.length > 0 && virtuosoRef.current) {
      const idx = flatList.findIndex(n => n.node.type === 'file' && n.node.path === selectedNodeId);
      if (idx !== -1) {
        // Use timeout to ensure Virtuoso has rendered the updated list
        setTimeout(() => {
          virtuosoRef.current?.scrollToIndex({
            index: idx,
            align: 'center',
            behavior: 'smooth'
          });
        }, 50);
      }
    }
  }, [selectedNodeId, flatList]);

  // Memoize item data props to prevent unnecessary inline objects
  const renderItem = useCallback((index: number, item: typeof flatList[0]) => (
    <FileNodeRow
      index={index}
      item={item}
      expandedFolders={expandedFolders}
      selectedNodeId={selectedNodeId}
      onSelectNode={onSelectNode}
      toggleFolder={toggleFolder}
      searchQuery={deferredQuery}
    />
  ), [expandedFolders, selectedNodeId, onSelectNode, toggleFolder, deferredQuery]);

  if (!data || !data.file_tree) return null;

  return (
    <div className="w-[300px] bg-surface-bright border-r border-outline-variant flex flex-col shrink-0 overflow-hidden h-full">
      {/* Header row */}
      <div className="px-4 pt-6 pb-3 flex flex-col gap-3 shrink-0">
        <div className="flex items-center justify-between">
          <h4 className="font-ui-label text-[12px] uppercase tracking-[0.1em] text-outline">
            Workspace
          </h4>
          <div className="flex items-center gap-1">
            <button
              onClick={expandAll}
              className="text-outline hover:text-on-surface transition-colors p-1 rounded hover:bg-surface-variant"
              title="Expand All"
            >
              <span className="material-symbols-outlined text-[16px]">unfold_more</span>
            </button>
            <button
              onClick={collapseAll}
              className="text-outline hover:text-on-surface transition-colors p-1 rounded hover:bg-surface-variant"
              title="Collapse All"
            >
              <span className="material-symbols-outlined text-[16px]">unfold_less</span>
            </button>
            <button
              onClick={() => {
                setSearchOpen(!searchOpen);
                if (searchOpen) setQuery("");
              }}
              className={`transition-colors p-1 rounded ${searchOpen ? "bg-surface-variant text-on-surface" : "text-outline hover:text-on-surface hover:bg-surface-variant"}`}
              title="Search files"
            >
              <span className="material-symbols-outlined text-[16px]">search</span>
            </button>
          </div>
        </div>

        {searchOpen && (
          <div className="flex items-center gap-2 w-full bg-surface-variant rounded-md px-2 py-1.5 border border-outline-variant focus-within:border-primary transition-colors">
            <span className="material-symbols-outlined text-[14px] text-outline shrink-0">
              search
            </span>
            <input
              autoFocus
              className="flex-1 bg-transparent border-none outline-none text-[13px] text-on-surface placeholder:text-outline font-body-md"
              placeholder="Filter files..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            {query && (
              <button
                onClick={() => setQuery("")}
                className="text-outline hover:text-on-surface flex items-center justify-center"
              >
                <span className="material-symbols-outlined text-[14px]">close</span>
              </button>
            )}
          </div>
        )}
      </div>

      {/* File list */}
      <div className="flex-1 w-full font-body-md text-[14px] pb-2 overflow-hidden">
        {flatList.length === 0 ? (
          <p className="text-outline text-[13px] py-4 px-6 italic">No files found.</p>
        ) : (
          <div className="w-full h-full">
            <Virtuoso
              ref={virtuosoRef}
              data={flatList}
              itemContent={renderItem}
              className="scrollbar-thin scrollbar-thumb-outline-variant scrollbar-track-transparent"
              style={{ height: '100%', width: '100%' }}
            />
          </div>
        )}
      </div>
    </div>
  );
}
