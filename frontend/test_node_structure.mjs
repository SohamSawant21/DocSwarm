import React from 'react';
import { renderToString } from 'react-dom/server';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const mdContent = `
Here is \`inline\` code.

\`\`\`
block code
\`\`\`
`;

const components = {
  code: (props) => {
    console.log("code node:", JSON.stringify(props.node, null, 2));
    return React.createElement('code', props);
  }
};

renderToString(
  React.createElement(ReactMarkdown, {
    remarkPlugins: [remarkGfm],
    components: components
  }, mdContent)
);
