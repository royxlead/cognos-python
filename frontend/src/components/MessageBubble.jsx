import React, { useState } from 'react';
import { User, Bot, Copy, ChevronDown, Brain } from 'lucide-react';
import ReasoningView from './ReasoningView';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

const MessageBubble = ({ message }) => {
  const [showReasoning, setShowReasoning] = useState(false);
  const isUser = message.role === 'user';
  const hasReasoning = message.reasoning_steps && message.reasoning_steps.length > 0;

  const copyToClipboard = () => {
    navigator.clipboard.writeText(message.content);
  };

  const CodeBlock = {
    code({ node, inline, className, children, ...props }) {
      const match = /language-(\w+)/.exec(className || '');
      return !inline && match ? (
        <SyntaxHighlighter
          style={oneDark}
          language={match[1]}
          PreTag="div"
          {...props}
        >
          {String(children).replace(/\n$/, '')}
        </SyntaxHighlighter>
      ) : (
        <code className={className} {...props}>
          {children}
        </code>
      );
    },
  };

  return (
    <div className={`flex items-start gap-4 animate-fade-in-up group ${isUser ? 'justify-end' : ''}`}>
      <div className={`flex-shrink-0 transition-transform duration-300 group-hover:scale-105 ${isUser ? 'avatar avatar-user' : 'avatar avatar-bot'}`}>
        {isUser ? <User size={18} /> : <Bot size={18} />}
      </div>

      <div className={`flex-1 max-w-2xl ${isUser ? 'order-first' : ''}`}>
        <div className={`glass-card p-5 transition-all duration-300 hover:shadow-lg ${
          isUser ? 'bg-primary/10 border-primary/20' : 'hover:bg-surface-glass/80'
        }`}>
          <div className="prose prose-slate dark:prose-invert prose-sm max-w-none
            prose-p:my-3 prose-p:leading-relaxed prose-headings:my-4 prose-headings:font-semibold
            prose-pre:bg-surface-solid prose-pre:p-4 prose-pre:rounded-lg prose-pre:shadow-inner
            prose-code:bg-surface-glass prose-code:px-2 prose-code:py-1 prose-code:rounded-md prose-code:text-sm
            prose-code:font-mono prose-strong:text-text prose-strong:font-semibold">
            <ReactMarkdown components={CodeBlock}>
              {message.content}
            </ReactMarkdown>
          </div>
        </div>

        {!isUser && !message.isError && (
          <div className="mt-4 flex items-center justify-between text-xs text-text-secondary opacity-0 group-hover:opacity-100 transition-opacity duration-300">
            <div className="flex items-center gap-4">
              {hasReasoning && (
                <button
                  onClick={() => setShowReasoning(!showReasoning)}
                  className="flex items-center gap-2 hover:text-text transition-all duration-200 p-2 rounded-lg hover:bg-surface-glass glass-hover"
                >
                  <Brain size={14} className={`transition-transform duration-200 ${showReasoning ? 'rotate-12' : ''}`} />
                  <span className='font-medium'>Reasoning</span>
                  <ChevronDown size={14} className={`transition-transform duration-200 ${showReasoning ? 'rotate-180' : ''}`} />
                </button>
              )}
              {message.confidence && (
                <div className="bg-surface-glass/80 backdrop-blur-sm px-3 py-1.5 rounded-full border border-border-glass/50">
                  <span className="font-medium text-text">Confidence: {(message.confidence * 100).toFixed(0)}%</span>
                </div>
              )}
            </div>
            <button
              onClick={copyToClipboard}
              className="p-2 hover:bg-surface-glass rounded-lg transition-all duration-200 glass-hover hover:scale-105"
              title="Copy to clipboard"
            >
              <Copy size={14} />
            </button>
          </div>
        )}

        {showReasoning && (
          <div className="mt-3">
            <ReasoningView steps={message.reasoning_steps} />
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageBubble;
