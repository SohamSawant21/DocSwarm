import React from 'react';
import { renderToString } from 'react-dom/server';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const originalError = console.error;
let errors = 0;
console.error = (...args) => {
  process.stdout.write("CAUGHT CONSOLE ERROR: " + args.join(" ") + "\n");
  errors++;
};

const mdContent = `
# Title
Normal paragraphs.

Here is some \`inline code\`.

\`\`\`js
console.log("single line code");
\`\`\`

\`\`\`python
def multi_line():
    print("hello")
    return True
\`\`\`

1. List item with \`code\`
2. Another item

## Headings followed by code
\`\`\`bash
npm install
\`\`\`

| A | B |
|---|---|
| 1 | 2 |
`;

const components = {
  h1: ({node, ...props}) => React.createElement('h1', props),
  p: ({node, ...props}) => React.createElement('p', props),
  ul: ({node, ...props}) => React.createElement('ul', props),
  ol: ({node, ...props}) => React.createElement('ol', props),
  li: ({node, ...props}) => React.createElement('li', props),
  pre: ({node, ...props}) => React.createElement('pre', { className: "[&>code]:bg-transparent" }, props.children),
  code: ({node, className, children, ...props}) => React.createElement('code', { className, ...props }, children),
  table: ({node, ...props}) => React.createElement('div', null, React.createElement('table', props)),
  th: ({node, ...props}) => React.createElement('th', props),
  td: ({node, ...props}) => React.createElement('td', props),
};

const html = renderToString(
  React.createElement(ReactMarkdown, {
    remarkPlugins: [remarkGfm],
    components: components
  }, mdContent)
);

console.log(html);
if (errors > 0) {
  process.exit(1);
}
