import React from "react";
import { ChevronRight, ChevronDown } from "lucide-react";
import type { FlatNode } from "@/hooks/useFileTree";
import { getIconForFile, getIconForFolder } from "@/utils/fileIcons";

export interface FileNodeRowProps {
  index: number;
  item: FlatNode;
  expandedFolders: Set<string>;
  selectedNodeId: string | null;
  onSelectNode: (id: string | null) => void;
  toggleFolder: (id: string) => void;
  searchQuery: string;
}

export const FileNodeRow = React.memo(({
  index,
  item,
  expandedFolders,
  selectedNodeId,
  onSelectNode,
  toggleFolder,
  searchQuery
}: FileNodeRowProps) => {
  const { node, level, id } = item;

  const isFolder = node.type === "folder";
  const isSelected = !isFolder && node.path === selectedNodeId;
  const expanded = searchQuery.trim() ? true : expandedFolders.has(id);

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isFolder) {
      toggleFolder(id);
    } else if (node.path) {
      onSelectNode(isSelected ? null : node.path);
    }
  };

  const paddingLeft = `${level * 0.75 + 1}rem`;

  // Highlight search text
  const renderName = () => {
    if (!searchQuery.trim()) return node.name;
    const lowerName = node.name.toLowerCase();
    const lowerQuery = searchQuery.trim().toLowerCase();
    const idx = lowerName.indexOf(lowerQuery);
    if (idx === -1) return node.name;

    return (
      <>
        {node.name.substring(0, idx)}
        <span className="bg-primary/20 text-primary font-medium rounded-sm px-0.5">
          {node.name.substring(idx, idx + lowerQuery.length)}
        </span>
        {node.name.substring(idx + lowerQuery.length)}
      </>
    );
  };

  return (
    <div className="pr-4 pl-2">
      <div
        onClick={handleClick}
        style={{ paddingLeft }}
        className={`flex items-center gap-1.5 cursor-pointer py-[0.2500rem] rounded group transition-all duration-100 select-none ${
          isSelected
            ? "bg-primary text-on-primary hover:bg-on-primary-fixed-variant"
            : "text-on-surface-variant hover:text-on-surface hover:bg-surface-variant"
        }`}
        title={node.path || node.name}
      >
        {isFolder ? (
          <div className="flex items-center justify-center w-4 h-4 text-outline hover:text-on-surface transition-colors">
            {expanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
          </div>
        ) : (
          <div className="w-4 h-4 flex-shrink-0" />
        )}

        {isFolder ? (
          (() => {
            const Icon = getIconForFolder(expanded).icon;
            return <Icon size={12} className={`flex-shrink-0 ${isSelected ? "text-on-primary" : "text-primary"}`} />;
          })()
        ) : (
          (() => {
            const Icon = getIconForFile(node.name).icon;
            return (
              <Icon 
                size={12} 
                className={`flex-shrink-0 ${
                  isSelected ? "text-on-primary" : "text-outline group-hover:text-primary"
                }`}
              />
            );
          })()
        )}

        <span className="truncate text-[0.8125rem] leading-tight">
          {renderName()}
        </span>
      </div>
    </div>
  );
});

FileNodeRow.displayName = "FileNodeRow";
