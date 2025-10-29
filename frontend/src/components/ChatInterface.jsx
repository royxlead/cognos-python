import React, { useState, useEffect, useRef } from 'react';
import { Send, Brain, CornerDownLeft } from 'lucide-react';
import MessageBubble from './MessageBubble';
import api, { sendMessage } from '../services/api';
import LoadingSpinner from './LoadingSpinner';

const ChatInterface = ({ conversationId, onConversationChange }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    const loadConversation = async () => {
      if (conversationId) {
        setIsLoading(true);
        try {
          const response = await api.get(`/api/conversations/${conversationId}`);
          setMessages(response.data.messages || []);
        } catch (err) {
          setError('Failed to load conversation.');
          console.error(err);
        } finally {
          setIsLoading(false);
        }
      } else {
        setMessages([{
          role: 'assistant',
          content: 'Hello! How can I help you today?',
          timestamp: new Date().toISOString(),
        }]);
      }
    };
    loadConversation();
  }, [conversationId]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = {
      role: 'user',
      content: input,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setError(null);

    try {
      const response = await sendMessage(input, 'gemini', true, conversationId);
      
      if (!conversationId) {
        onConversationChange(response.session_id);
      }

      const assistantMessage = {
        role: 'assistant',
        content: response.answer,
        timestamp: new Date().toISOString(),
        reasoning_steps: response.reasoning_steps || [],
        memories_used: response.memories_used,
        confidence: response.confidence,
        method: response.method,
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (err) {
      console.error('Error sending message:', err);
      const errorMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString(),
        isError: true,
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto">
      <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
        {messages.length === 0 && !isLoading && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="avatar avatar-bot mb-4">
              <Brain size={24} />
            </div>
            <h3 className="text-xl font-semibold text-text mb-2">Welcome to Cognos</h3>
            <p className="text-text-secondary max-w-md">
              I'm your AI assistant with memory capabilities. Ask me anything and I'll remember our conversations to provide better responses.
            </p>
          </div>
        )}

        {messages.map((message, index) => (
          <MessageBubble key={index} message={message} />
        ))}

        {isLoading && !messages.some(m => m.role === 'assistant' && m.content.includes('thinking')) && (
          <div className="flex justify-center">
            <LoadingSpinner />
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="p-6 pt-0 animate-slide-in-right">
        <div className="glass-card p-5 shadow-lg">
          <div className="relative">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask anything..."
              className="glass-input w-full resize-none pr-28 pl-5 py-4 bg-transparent border-0 focus:ring-0 text-text placeholder-text-muted text-base leading-relaxed smooth-focus"
              rows="1"
              disabled={isLoading}
              onInput={(e) => {
                e.target.style.height = 'auto';
                e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
              }}
            />
            <div className="absolute right-4 top-1/2 -translate-y-1/2 flex items-center gap-3">
              <button
                onClick={handleSend}
                disabled={!input.trim() || isLoading}
                className={`btn-glass-primary h-10 w-10 p-0 rounded-xl flex items-center justify-center transition-all duration-300 ${
                  !input.trim() || isLoading ? 'opacity-50 cursor-not-allowed scale-95' : 'hover:scale-110 shadow-lg'
                }`}
              >
                <Send size={18} className={`transition-transform duration-200 ${input.trim() && !isLoading ? 'group-hover:translate-x-0.5 group-hover:-translate-y-0.5' : ''}`} />
              </button>
              <div className="text-xs text-text-secondary hidden lg:flex items-center gap-1.5">
                <kbd className="font-sans bg-surface-glass border border-border-glass rounded-lg px-2 py-1 text-xs font-medium shadow-sm">
                  Enter
                </kbd>
                <span className="font-medium">to send</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;
