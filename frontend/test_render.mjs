import React from 'react';
import { renderToString } from 'react-dom/server';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const mdContent = `
# Title

Here is a paragraph with some \`inline code\`.

And here is a block:
\`\`\`js
console.log("hello");
\`\`\`

Here is a table:
| A | B |
|---|---|
| 1 | 2 |
`;

const components = {
  h1: ({node, ...props}) => React.createElement('h1', props),
  h2: ({node, ...props}) => React.createElement('h2', props),
  h3: ({node, ...props}) => React.createElement('h3', props),
  p: ({node, ...props}) => React.createElement('p', props),
  ul: ({node, ...props}) => React.createElement('ul', props),
  ol: ({node, ...props}) => React.createElement('ol', props),
  li: ({node, ...props}) => React.createElement('li', props),
  code: ({node, inline, className, children, ...props}) => {
    const match = /language-(\w+)/.exec(className || '');
    return !inline ? (
      React.createElement('pre', { className: "bg-[#1e1e1e]" },
        React.createElement('code', { className, ...props }, children)
      )
    ) : (
      React.createElement('code', { className: "bg-surface-variant", ...props }, children)
    );
  },
  blockquote: ({node, ...props}) => React.createElement('blockquote', props),
  table: ({node, ...props}) => React.createElement('div', null, React.createElement('table', props)),
  th: ({node, ...props}) => React.createElement('th', props),
  td: ({node, ...props}) => React.createElement('td', props),
};

try {
  const html = renderToString(
    React.createElement(ReactMarkdown, {
      remarkPlugins: [remarkGfm],
      components: components
    }, mdContent)
  );
  console.log("HTML:", html);
} catch (error) {
  console.error("ERROR CAUGHT:", error);
}
