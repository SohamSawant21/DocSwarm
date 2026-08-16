import React from 'react';
import { renderToString } from 'react-dom/server';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const originalError = console.error;
console.error = (...args) => {
  process.stdout.write("CAUGHT CONSOLE ERROR: " + args.join(" ") + "\n");
};

const mdContent = `
\`\`\`js
console.log();
\`\`\`
`;

const components = {
  code: ({node, inline, className, children, ...props}) => {
    return (
      React.createElement('pre', null, 
        React.createElement('code', { className, ...props }, children)
      )
    );
  }
};

renderToString(
  React.createElement(ReactMarkdown, {
    remarkPlugins: [remarkGfm],
    components: components
  }, mdContent)
);
