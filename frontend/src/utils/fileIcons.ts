import { 
  FileCode2, 
  FileJson, 
  Package, 
  Container, 
  Key, 
  BookOpen, 
  Database, 
  AppWindow, 
  Image as ImageIcon, 
  FileText, 
  File, 
  Folder, 
  FolderOpen,
  type LucideIcon
} from "lucide-react";

export type IconData = {
  icon: LucideIcon;
};

// Exact filename matches (highest priority)
const exactMatches: Record<string, LucideIcon> = {
  "package.json": Package,
  "package-lock.json": Package,
  "yarn.lock": Package,
  "dockerfile": Container,
  "docker-compose.yml": Container,
  ".env": Key,
  "secrets.json": Key,
  "readme.md": BookOpen,
  "database.sqlite": Database,
  "database.db": Database,
};

// Extension matches (lower priority)
const extensionMatches: Record<string, LucideIcon> = {
  "py": FileCode2,
  "js": FileCode2,
  "jsx": FileCode2,
  "ts": FileCode2,
  "tsx": FileCode2,
  "go": FileCode2,
  "rs": FileCode2,
  "cpp": FileCode2,
  "c": FileCode2,
  "java": FileCode2,
  "cs": FileCode2,
  "php": FileCode2,
  "rb": FileCode2,
  "swift": FileCode2,
  "kt": FileCode2,
  "sh": FileCode2,
  
  "html": AppWindow,
  "css": AppWindow,
  "scss": AppWindow,
  "less": AppWindow,

  "json": FileJson,
  "yaml": FileJson,
  "yml": FileJson,
  "xml": FileJson,

  "png": ImageIcon,
  "jpg": ImageIcon,
  "jpeg": ImageIcon,
  "svg": ImageIcon,
  "gif": ImageIcon,

  "md": FileText,
  "txt": FileText,
  "csv": FileText,
  "sql": Database,
};

/**
 * Returns the appropriate lucide-react icon component for a given file name.
 */
export function getIconForFile(filename: string): IconData {
  if (!filename) return { icon: File };

  const lowerName = filename.split("/").pop()?.toLowerCase() || "";

  // 1. Check exact matches
  if (exactMatches[lowerName]) {
    return { icon: exactMatches[lowerName] };
  }

  // 2. Extract extension and check extension matches
  const parts = lowerName.split(".");
  if (parts.length > 1) {
    const ext = parts[parts.length - 1];
    if (extensionMatches[ext]) {
      return { icon: extensionMatches[ext] };
    }
  }

  // 3. Fallback
  return { icon: File };
}

/**
 * Returns the appropriate lucide-react icon for a folder.
 */
export function getIconForFolder(isOpen: boolean): IconData {
  return { icon: isOpen ? FolderOpen : Folder };
}
