import React, { useState } from 'react';
import { MessageSquare, Brain, Settings, Plus, Sparkles } from 'lucide-react';
import ChatInterface from './components/ChatInterface';
import MemoryDashboard from './components/MemoryDashboard';
import SettingsPanel from './components/SettingsPanel';
import ConversationHistory from './components/ConversationHistory';
import ThemeToggle from './components/ThemeToggle';

const App = () => {
  const [activeView, setActiveView] = useState('chat');
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [showSettings, setShowSettings] = useState(false);
  const [conversationCount, setConversationCount] = useState(0);

  const navItems = [
    { id: 'chat', icon: MessageSquare, label: 'Chat' },
    { id: 'memory', icon: Brain, label: 'Memory' },
  ];

  const handleSelectConversation = (id) => {
    setCurrentConversationId(id);
    setActiveView('chat');
  };

  const handleNewChat = () => {
    setCurrentConversationId(null);
    setActiveView('chat');
  };

  return (
    <div className='min-h-screen bg-bg flex animate-fade-in-up'>
      <aside className='glass-card m-6 rounded-3xl w-80 flex flex-col shadow-2xl'>
        <div className='p-6 border-b border-border-glass/50'>
          <div className='flex items-center justify-between'>
            <div className='flex items-center gap-3'>
              <div className='avatar glow-primary animate-pulse-subtle'>
                <Sparkles size={20} />
              </div>
              <div className='animate-slide-in-right'>
                <h1 className='text-xl font-bold text-text text-gradient'>Cognos</h1>
                <p className='text-xs text-text-secondary'>AI Assistant</p>
              </div>
            </div>
            <ThemeToggle />
          </div>
        </div>

        <div className='p-4'>
          <button
            onClick={handleNewChat}
            className='btn-glass-primary w-full flex items-center justify-center gap-2 group transition-all duration-300'
          >
            <Plus size={18} className='group-hover:rotate-90 transition-transform duration-300' />
            <span>New Chat</span>
          </button>
        </div>

        <nav className='px-4 pb-4'>
          <ul className='space-y-2'>
            {navItems.map((item) => (
              <li key={item.id}>
                <button
                  onClick={() => setActiveView(item.id)}
                  className={`w-full flex items-center justify-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 glass-hover smooth-focus ${
                    activeView === item.id
                      ? 'bg-primary/20 text-primary glow-primary shadow-lg'
                      : 'text-text-secondary hover:bg-surface-glass hover:text-text'
                  }`}
                >
                  <item.icon size={20} className={`transition-transform duration-200 ${
                    activeView === item.id ? 'scale-110' : ''
                  }`} />
                  <span className='font-medium'>{item.label}</span>
                </button>
              </li>
            ))}
          </ul>
        </nav>

        <div className='flex-1 px-4 pb-4 min-h-0'>
          <div className='text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3 px-1'>
            Conversations
          </div>
          <ConversationHistory
            onSelectConversation={handleSelectConversation}
            currentConversationId={currentConversationId}
            onConversationCountChange={setConversationCount}
          />
        </div>


      </aside>

      <main className='flex-1 flex flex-col m-6 mr-6'>
        <header className='glass-card rounded-3xl p-6 mb-6 flex items-center justify-between shadow-xl animate-slide-in-right'>
          <div className='flex-1'>
            <h1 className='text-2xl font-bold text-text text-gradient'>
              {navItems.find(item => item.id === activeView)?.label || 'Chat'}
            </h1>
            <p className='text-text-secondary mt-1 text-sm'>
              {activeView === 'chat'
                ? 'Have a conversation with your AI assistant'
                : 'Explore and manage your memory system'
              }
            </p>
          </div>
          <button
            onClick={() => setShowSettings(true)}
            className='btn-glass-secondary flex items-center gap-2 px-4 py-2 group hover:scale-105 transition-transform duration-200'
          >
            <Settings size={18} className='group-hover:rotate-90 transition-transform duration-300' />
            <span>Settings</span>
          </button>
        </header>

        <div className='flex-1 glass-card rounded-3xl p-6 overflow-hidden shadow-2xl animate-fade-in-up transition-all duration-300'>
          {activeView === 'chat' && (
            <ChatInterface
              key={currentConversationId}
              conversationId={currentConversationId}
              onConversationChange={setCurrentConversationId}
            />
          )}
          {activeView === 'memory' && <MemoryDashboard />}
        </div>
      </main>

      {showSettings && (
        <SettingsPanel onClose={() => setShowSettings(false)} />
      )}
    </div>
  );
};

export default App;
