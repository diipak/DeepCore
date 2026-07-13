import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownViewerProps {
  content: string;
}

export const MarkdownViewer: React.FC<MarkdownViewerProps> = ({ content }) => {
  return (
    <div className="prose dark:prose-invert max-w-none text-text-primary select-text leading-relaxed">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h1 className="text-2xl font-extrabold text-text-primary mt-6 mb-3 tracking-tight border-b border-border-primary pb-2">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-xl font-bold text-text-primary mt-5 mb-2.5 tracking-tight">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-lg font-bold text-text-primary mt-4 mb-2">
              {children}
            </h3>
          ),
          p: ({ children }) => (
            <p className="text-sm md:text-base text-text-secondary leading-relaxed mb-4 max-w-3xl">
              {children}
            </p>
          ),
          ul: ({ children }) => (
            <ul className="list-disc pl-5 mb-4 text-text-secondary text-sm md:text-base space-y-1.5">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal pl-5 mb-4 text-text-secondary text-sm md:text-base space-y-1.5">
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className="leading-relaxed">
              {children}
            </li>
          ),
          a: ({ href, children }) => (
            <a 
              href={href} 
              target="_blank" 
              rel="noopener noreferrer" 
              className="text-accent-primary hover:underline font-semibold"
            >
              {children}
            </a>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-accent-memory/40 bg-accent-memory/5 px-4 py-2 rounded-r-lg italic my-4 text-text-secondary">
              {children}
            </blockquote>
          ),
          code: ({ className, children }) => {
            const isInline = !className || !className.includes('language-');
            const match = /language-(\w+)/.exec(className || '');
            const lang = match ? match[1] : '';

            if (isInline) {
              return (
                <code className="px-1.5 py-0.5 rounded bg-background-primary border border-border-primary font-mono text-xs text-text-primary">
                  {children}
                </code>
              );
            }
            return (
              <div className="my-4 border border-border-primary rounded-xl overflow-hidden shadow-inner">
                {lang && (
                  <div className="flex items-center justify-between px-4 py-1.5 bg-background-primary border-b border-border-primary/80 select-none">
                    <span className="text-[10px] font-bold text-text-secondary uppercase tracking-widest">{lang}</span>
                  </div>
                )}
                <pre className="p-4 font-mono text-xs md:text-sm bg-background-primary overflow-x-auto text-text-primary leading-relaxed">
                  <code>{children}</code>
                </pre>
              </div>
            );
          },
          table: ({ children }) => (
            <div className="overflow-x-auto w-full border border-border-primary rounded-xl mb-4 bg-surface-card shadow-sm">
              <table className="w-full border-collapse text-sm text-left">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-background-primary border-b border-border-primary">
              {children}
            </thead>
          ),
          tbody: ({ children }) => (
            <tbody className="divide-y divide-border-primary/50">
              {children}
            </tbody>
          ),
          th: ({ children }) => (
            <th className="px-4 py-2.5 font-bold text-text-primary text-xs uppercase tracking-wider">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="px-4 py-3 text-text-secondary">
              {children}
            </td>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};
