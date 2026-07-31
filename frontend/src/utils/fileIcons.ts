export type IconData = {
  type: "devicon" | "material";
  className: string;
};

// Exact filename matches (highest priority)
const exactMatches: Record<string, IconData> = {
  "package.json": { type: "devicon", className: "devicon-npm-original-wordmark colored" },
  "package-lock.json": { type: "devicon", className: "devicon-npm-original-wordmark colored" },
  "yarn.lock": { type: "devicon", className: "devicon-yarn-plain colored" },
  "dockerfile": { type: "devicon", className: "devicon-docker-plain colored" },
  "docker-compose.yml": { type: "devicon", className: "devicon-docker-plain colored" },
  ".gitignore": { type: "devicon", className: "devicon-git-plain colored" },
  "tsconfig.json": { type: "devicon", className: "devicon-typescript-plain colored" },
  "webpack.config.js": { type: "devicon", className: "devicon-webpack-plain colored" },
  "readme.md": { type: "devicon", className: "devicon-markdown-original colored" },
  "next.config.js": { type: "devicon", className: "devicon-nextjs-original" },
  "next.config.mjs": { type: "devicon", className: "devicon-nextjs-original" }
};

// Extension matches (lower priority)
const extensionMatches: Record<string, IconData> = {
  "py": { type: "devicon", className: "devicon-python-plain colored" },
  "js": { type: "devicon", className: "devicon-javascript-plain colored" },
  "jsx": { type: "devicon", className: "devicon-react-original colored" },
  "ts": { type: "devicon", className: "devicon-typescript-plain colored" },
  "tsx": { type: "devicon", className: "devicon-react-original colored" },
  "html": { type: "devicon", className: "devicon-html5-plain colored" },
  "css": { type: "devicon", className: "devicon-css3-plain colored" },
  "scss": { type: "devicon", className: "devicon-sass-original colored" },
  "less": { type: "devicon", className: "devicon-less-plain-wordmark colored" },
  "json": { type: "material", className: "data_object" }, // Generic JSON
  "md": { type: "devicon", className: "devicon-markdown-original colored" },
  "rs": { type: "devicon", className: "devicon-rust-original" },
  "go": { type: "devicon", className: "devicon-go-original-wordmark colored" },
  "java": { type: "devicon", className: "devicon-java-plain colored" },
  "cpp": { type: "devicon", className: "devicon-cplusplus-plain colored" },
  "c": { type: "devicon", className: "devicon-c-plain colored" },
  "cs": { type: "devicon", className: "devicon-csharp-plain colored" },
  "php": { type: "devicon", className: "devicon-php-plain colored" },
  "rb": { type: "devicon", className: "devicon-ruby-plain colored" },
  "swift": { type: "devicon", className: "devicon-swift-plain colored" },
  "kt": { type: "devicon", className: "devicon-kotlin-plain colored" },
  "yml": { type: "material", className: "list_alt" },
  "yaml": { type: "material", className: "list_alt" },
  "xml": { type: "material", className: "code" },
  "sh": { type: "devicon", className: "devicon-bash-plain colored" },
  "sql": { type: "material", className: "database" },
  "png": { type: "material", className: "image" },
  "jpg": { type: "material", className: "image" },
  "jpeg": { type: "material", className: "image" },
  "svg": { type: "material", className: "image" },
};

/**
 * Returns the appropriate icon data for a given file name.
 */
export function getIconForFile(filename: string): IconData {
  if (!filename) return { type: "material", className: "description" };

  const lowerName = filename.split("/").pop()?.toLowerCase() || "";

  // 1. Check exact matches
  if (exactMatches[lowerName]) {
    return exactMatches[lowerName];
  }

  // 2. Extract extension and check extension matches
  const parts = lowerName.split(".");
  if (parts.length > 1) {
    const ext = parts[parts.length - 1];
    if (extensionMatches[ext]) {
      return extensionMatches[ext];
    }
  }

  // 3. Fallback
  return { type: "material", className: "description" };
}

/**
 * Returns the appropriate icon data for a folder.
 */
export function getIconForFolder(isOpen: boolean): IconData {
  return { 
    type: "material", 
    className: isOpen ? "folder_open" : "folder" 
  };
}
