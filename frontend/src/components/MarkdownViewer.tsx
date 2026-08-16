import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function MarkdownViewer({ content }: { content: string }) {
  return (
    <div className="prose prose-slate max-w-none prose-headings:font-display prose-a:text-primary">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ node, ...props }) => <h1 className="text-3xl font-bold mt-8 mb-4 border-b pb-2 border-outline-variant" {...props} />,
          h2: ({ node, ...props }) => <h2 className="text-2xl font-semibold mt-6 mb-3" {...props} />,
          h3: ({ node, ...props }) => <h3 className="text-xl font-semibold mt-4 mb-2" {...props} />,
          p: ({ node, ...props }) => <p className="mb-4 text-on-surface leading-relaxed" {...props} />,
          ul: ({ node, ...props }) => <ul className="list-disc pl-6 mb-4 space-y-1" {...props} />,
          ol: ({ node, ...props }) => <ol className="list-decimal pl-6 mb-4 space-y-1" {...props} />,
          li: ({ node, ...props }) => <li className="text-on-surface" {...props} />,
          pre: ({ node, ...props }) => (
            <pre className="bg-[#1e1e1e] text-[#d4d4d4] p-4 rounded-lg overflow-x-auto my-4 text-sm font-mono border border-outline-variant [&>code]:bg-transparent [&>code]:text-inherit [&>code]:p-0 [&>code]:rounded-none" {...props} />
          ),
          code: ({ node, className, children, ...props }: any) => {
            return (
              <code className={`bg-surface-variant text-on-surface px-1.5 py-0.5 rounded text-sm font-mono ${className || ''}`.trim()} {...props}>
                {children}
              </code>
            );
          },
          blockquote: ({ node, ...props }) => <blockquote className="border-l-4 border-primary pl-4 italic text-on-surface-variant my-4 bg-surface-variant/30 py-2 rounded-r-lg" {...props} />,
          table: ({ node, ...props }) => <div className="overflow-x-auto my-6"><table className="w-full text-left border-collapse" {...props} /></div>,
          th: ({ node, ...props }) => <th className="border-b-2 border-outline-variant p-3 font-semibold bg-surface-variant/50" {...props} />,
          td: ({ node, ...props }) => <td className="border-b border-outline-variant p-3" {...props} />,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
