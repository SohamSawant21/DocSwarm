import React from 'react';
import { renderToString } from 'react-dom/server';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const originalError = console.error;
console.error = (...args) => {
  process.stdout.write("CAUGHT CONSOLE ERROR: " + args.join(" ") + "\n");
};

const mdContent = `
# Title

Here is a table:
| A | B |
|---|---|
| 1 | 2 |
`;

const components = {
  table: ({node, ...props}) => React.createElement('div', null, React.createElement('table', props)),
  th: ({node, ...props}) => React.createElement('th', props),
  td: ({node, ...props}) => React.createElement('td', props),
};

renderToString(
  React.createElement(ReactMarkdown, {
    remarkPlugins: [remarkGfm],
    components: components
  }, mdContent)
);
