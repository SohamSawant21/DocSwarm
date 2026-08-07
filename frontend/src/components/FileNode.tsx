import React, { useState } from "react";
import { ChevronRight, ChevronDown } from "lucide-react";
import type { FileTreeNode } from "@/types";
import { getIconForFile, getIconForFolder } from "@/utils/fileIcons";

export interface FileNodeProps {
  node: FileTreeNode;
  level: number;
  selectedNodeId: string | null;
  onSelectNode: (id: string | null) => void;
  searchQuery?: string;
}

export const FileNode: React.FC<FileNodeProps> = React.memo(({
  node,
  level,
  selectedNodeId,
  onSelectNode,
  searchQuery = ""
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const isFolder = node.type === "folder";
  const isSelected = !isFolder && node.path === selectedNodeId;

  // Filter children based on search query
  const hasMatch = (n: FileTreeNode, q: string): boolean => {
    if (n.name.toLowerCase().includes(q.toLowerCase())) return true;
    if (n.type === "folder" && n.children) {
      return n.children.some(child => hasMatch(child, q));
    }
    return false;
  };

  if (searchQuery.trim() && !hasMatch(node, searchQuery)) {
    return null;
  }

  // Force expand if searching
  const expanded = (searchQuery.trim() !== "") ? true : isExpanded;

  const toggleExpand = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsExpanded(prev => !prev);
  };

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isFolder) {
      toggleExpand(e);
    } else if (node.path) {
      onSelectNode(isSelected ? null : node.path);
    }
  };

  const paddingLeft = `${level * 12 + 8}px`;

  return (
    <div>
      <div
        onClick={handleClick}
        style={{ paddingLeft }}
        className={`flex items-center gap-1.5 cursor-pointer py-1 pr-2 rounded group transition-all duration-200 select-none ${
          isSelected
            ? "bg-primary text-on-primary hover:bg-on-primary-fixed-variant"
            : "text-on-surface-variant hover:text-on-surface hover:bg-surface-variant"
        }`}
        title={node.path || node.name}
      >
        {isFolder ? (
          <div className="flex items-center justify-center w-4 h-4 text-outline hover:text-on-surface transition-colors" onClick={toggleExpand}>
            {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </div>
        ) : (
          <div className="w-4 h-4 flex-shrink-0" /> // Spacer for alignment
        )}

        {isFolder ? (
          (() => {
            const Icon = getIconForFolder(expanded).icon;
            return <Icon size={16} className="text-primary flex-shrink-0" />;
          })()
        ) : (
          (() => {
            const Icon = getIconForFile(node.name).icon;
            return (
              <Icon 
                size={16} 
                className={`flex-shrink-0 ${
                  isSelected ? "text-on-primary" : "text-outline group-hover:text-primary"
                }`}
              />
            );
          })()
        )}

        <span className="truncate text-[13px]">
          {node.name}
        </span>
      </div>

      {isFolder && expanded && node.children && (
        <div className="flex flex-col">
          {node.children.map((child, index) => (
            <FileNode
              key={`${child.path || child.name}-${index}`}
              node={child}
              level={level + 1}
              selectedNodeId={selectedNodeId}
              onSelectNode={onSelectNode}
              searchQuery={searchQuery}
            />
          ))}
        </div>
      )}
    </div>
  );
});

FileNode.displayName = "FileNode";
