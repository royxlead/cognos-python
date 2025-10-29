import { useState, useEffect } from 'react';
import { Trash2, MessageSquare } from 'lucide-react';
import api from '../services/api';
import LoadingSpinner from './LoadingSpinner';

const ConversationHistory = ({ onSelectConversation, currentConversationId, onConversationCountChange }) => {
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/conversations');
      const convs = response.data.conversations || [];
      convs.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
      setConversations(convs);
      setError(null);
      if (onConversationCountChange) {
        onConversationCountChange(convs.length);
      }
    } catch (err) {
      console.error('Failed to load conversations:', err);
      setError('Failed to load conversations');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (e, sessionId) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this conversation?')) {
      return;
    }
    try {
      await api.delete(`/api/conversations/${sessionId}`);
      setConversations(conversations.filter(c => c.session_id !== sessionId));
      if (sessionId === currentConversationId) {
        onSelectConversation(null);
      }
    } catch (err) {
      console.error('Failed to delete conversation:', err);
      alert('Failed to delete conversation');
    }
  };

  const parseDate = (s) => {
    if (!s) return new Date();
    const hasTZ = /([Z]|[+-]\d\d:\d\d)$/.test(s);
    return new Date(hasTZ ? s : s + 'Z');
  };

  const formatDate = (dateString) => {
    const date = parseDate(dateString);
    const now = new Date();
    const diff = now - date;
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) {
      const hours = Math.floor(diff / (1000 * 60 * 60));
      if (hours === 0) {
        const minutes = Math.floor(diff / (1000 * 60));
        return minutes < 2 ? 'Just now' : `${minutes}m ago`;
      }
      return `${hours}h ago`;
    }
    if (days === 1) return 'Yesterday';
    if (days < 7) return `${days}d ago`;
    return date.toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <LoadingSpinner />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-center text-red-500 text-sm">
        <p>{error}</p>
        <button onClick={loadConversations} className="btn btn-secondary mt-2">
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto -mr-2 pr-2">
      {conversations.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-full p-4 text-center">
          <MessageSquare className="w-10 h-10 text-text-tertiary mb-2" />
          <p className="text-sm text-text-secondary">No conversations yet.</p>
        </div>
      ) : (
        <ul className="space-y-1">
          {conversations.map((conv) => (
            <li key={conv.session_id}>
              <button
                onClick={() => onSelectConversation(conv.session_id)}
                className={`group w-full text-left p-2 rounded-md transition-colors
                  ${
                    conv.session_id === currentConversationId
                      ? 'bg-primary/10'
                      : 'hover:bg-surface-inset'
                  }
                `}
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1 min-w-0">
                    <h3
                      className={`text-sm font-medium truncate
                        ${
                          conv.session_id === currentConversationId
                            ? 'text-primary'
                            : 'text-text'
                        }
                      `}
                    >
                      {conv.title || 'Untitled Conversation'}
                    </h3>
                    <p className="text-xs text-text-secondary truncate">
                      {formatDate(conv.updated_at)}
                    </p>
                  </div>
                  <div
                    onClick={(e) => handleDelete(e, conv.session_id)}
                    className="p-1 rounded-md opacity-0 group-hover:opacity-100 hover:bg-red-500/10 text-text-tertiary hover:text-red-500 transition-opacity"
                    title="Delete conversation"
                  >
                    <Trash2 size={14} />
                  </div>
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default ConversationHistory;
