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
  code: (props) => {
    console.log("code props keys:", Object.keys(props));
    console.log("has node?", 'node' in props);
    return React.createElement('code', props);
  }
};

renderToString(
  React.createElement(ReactMarkdown, {
    remarkPlugins: [remarkGfm],
    components: components
  }, mdContent)
);
