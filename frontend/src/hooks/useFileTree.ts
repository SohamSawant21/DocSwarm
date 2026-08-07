import { useState, useMemo, useEffect, useCallback } from "react";
import type { FileTreeNode } from "@/types";

export interface FlatNode {
  node: FileTreeNode;
  level: number;
  id: string;
}

export function useFileTree(
  tree: FileTreeNode[],
  selectedNodeId: string | null,
  query: string
) {
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());

  // Auto-expand parents when selectedNodeId changes
  useEffect(() => {
    if (selectedNodeId) {
      const parts = selectedNodeId.split('/');
      const newExpanded = new Set(expandedFolders);
      let current = "";
      let changed = false;
      for (let i = 0; i < parts.length - 1; i++) {
        current = current ? `${current}/${parts[i]}` : parts[i];
        if (!newExpanded.has(current)) {
          newExpanded.add(current);
          changed = true;
        }
      }
      if (changed) {
        setExpandedFolders(newExpanded);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedNodeId]);

  const toggleFolder = useCallback((id: string) => {
    setExpandedFolders(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const expandAll = useCallback(() => {
    const allFolders = new Set<string>();
    const traverse = (nodes: FileTreeNode[], parentPath: string) => {
      for (const n of nodes) {
        const id = parentPath ? `${parentPath}/${n.name}` : n.name;
        if (n.type === 'folder') {
          allFolders.add(id);
          if (n.children) traverse(n.children, id);
        }
      }
    };
    traverse(tree, "");
    setExpandedFolders(allFolders);
  }, [tree]);

  const collapseAll = useCallback(() => {
    setExpandedFolders(new Set());
  }, []);

  const flatList = useMemo(() => {
    const list: FlatNode[] = [];

    const hasMatch = (n: FileTreeNode, q: string): boolean => {
      if (n.name.toLowerCase().includes(q.toLowerCase())) return true;
      if (n.type === "folder" && n.children) {
        return n.children.some(child => hasMatch(child, q));
      }
      return false;
    };

    const traverse = (nodes: FileTreeNode[], level: number, parentPath: string) => {
      for (const node of nodes) {
        const id = parentPath ? `${parentPath}/${node.name}` : node.name;
        
        if (query.trim() && !hasMatch(node, query.trim())) {
          continue;
        }

        list.push({ node, level, id });

        const isExpanded = query.trim() ? true : expandedFolders.has(id);

        if (node.type === "folder" && isExpanded && node.children) {
          traverse(node.children, level + 1, id);
        }
      }
    };

    traverse(tree, 0, "");
    return list;
  }, [tree, expandedFolders, query]);

  return {
    flatList,
    expandedFolders,
    toggleFolder,
    expandAll,
    collapseAll
  };
}
