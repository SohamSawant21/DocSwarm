import React from 'react';
import { renderToString } from 'react-dom/server';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const mdContent = `
| A | B |
|---|---|
| 1 | 2 |
`;

const components = {
  th: ({node, ...props}) => {
    console.log("th props:", Object.keys(props));
    return React.createElement('th', props);
  },
  td: ({node, ...props}) => {
    console.log("td props:", Object.keys(props));
    return React.createElement('td', props);
  },
};

renderToString(
  React.createElement(ReactMarkdown, {
    remarkPlugins: [remarkGfm],
    components: components
  }, mdContent)
);
