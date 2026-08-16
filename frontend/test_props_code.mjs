import React from 'react';
import { renderToString } from 'react-dom/server';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const mdContent = `
Here is \`inline\` code.

\`\`\`js
console.log();
\`\`\`
`;

const components = {
  code: ({node, ...props}) => {
    console.log("code props:", Object.keys(props));
    return React.createElement('code', props);
  }
};

renderToString(
  React.createElement(ReactMarkdown, {
    remarkPlugins: [remarkGfm],
    components: components
  }, mdContent)
);
