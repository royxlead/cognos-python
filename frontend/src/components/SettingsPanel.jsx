import React, { useState, useEffect } from 'react';
import { X, Key, Database, Brain, Download, Upload, Trash2, Settings, Shield, Palette, Cpu } from 'lucide-react';
import { clearAllMemories, exportMemories } from '../services/api';

function SettingsPanel({ onClose }) {
  const [apiKeys, setApiKeys] = useState({
    gemini: '',
    openai: '',
  });

  const [settings, setSettings] = useState({
    maxMemories: 1000,
    memoryDecayDays: 90,
    enableCoT: true,
    maxReasoningSteps: 5,
  });

  const [models, setModels] = useState([]);
  const [currentModel, setCurrentModel] = useState('gemini');

  useEffect(() => {
    fetchAvailableModels();
  }, []);

  const fetchAvailableModels = async () => {
    try {
      const response = await fetch('/api/models');
      if (response.ok) {
        const data = await response.json();
        setModels(data.models || []);
        const current = data.models?.find(m => m.current);
        if (current) setCurrentModel(current.name);
      }
    } catch (error) {
      console.error('Error fetching models:', error);
    }
  };

  const switchModel = async (modelName) => {
    try {
      const response = await fetch('/api/models/switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: modelName })
      });
      if (response.ok) {
        setCurrentModel(modelName);
        alert(`Switched to ${modelName} model`);
      } else {
        alert('Failed to switch model');
      }
    } catch (error) {
      console.error('Error switching model:', error);
      alert('Failed to switch model');
    }
  };

  const handleClearMemories = async () => {
    if (window.confirm('Are you sure you want to clear all memories? This action cannot be undone.')) {
      try {
        await clearAllMemories();
        alert('All memories cleared successfully');
      } catch (error) {
        console.error('Error clearing memories:', error);
        alert('Failed to clear memories');
      }
    }
  };

  const handleExport = async () => {
    try {
      const data = await exportMemories();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `cognos-memories-${new Date().toISOString()}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error exporting memories:', error);
      alert('Failed to export memories');
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-30 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-fade-in-up">
      <div className="glass-card w-full max-w-4xl max-h-[90vh] overflow-hidden animate-fade-in-up shadow-2xl">
        <div className="flex items-center justify-between p-6 border-b border-border-glass/50">
          <div className="flex items-center space-x-3">
            <div className="avatar glow-primary animate-pulse-subtle">
              <Settings className="w-6 h-6 text-primary" />
            </div>
            <div className="animate-slide-in-right">
              <h2 className="text-2xl font-bold text-text text-gradient">Settings</h2>
              <p className="text-text-secondary text-sm">Customize your COGNOS experience</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-3 hover:bg-surface-glass rounded-xl transition-all duration-200 hover:scale-105 glass-hover"
          >
            <X className="w-6 h-6 text-text-secondary" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto custom-scrollbar p-6">
          <div className="glass-card mb-6 animate-fade-in-up">
            <div className="flex items-center space-x-3 mb-6">
              <div className="p-2 bg-accent/20 rounded-xl animate-pulse-subtle">
                <Cpu className="w-5 h-5 text-accent" />
              </div>
              <div className="animate-slide-in-right">
                <h3 className="text-lg font-semibold text-text text-gradient">AI Model Selection</h3>
                <p className="text-text-secondary text-sm">Choose your AI provider for up-to-date responses</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {models.map((model, index) => (
                <div
                  key={model.name}
                  className={`p-5 rounded-xl border-2 transition-all duration-300 cursor-pointer glass-hover animate-fade-in-up ${
                    model.name === currentModel
                      ? 'border-primary bg-primary/10 glow-primary shadow-lg scale-105'
                      : 'border-border-glass bg-surface-glass hover:border-primary/50 hover:scale-102'
                  } ${!model.available ? 'opacity-50 cursor-not-allowed grayscale' : ''}`}
                  style={{ animationDelay: `${index * 100}ms` }}
                  onClick={() => model.available && switchModel(model.name)}
                >
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-sm font-semibold text-text capitalize">{model.name}</span>
                    <div className={`w-3 h-3 rounded-full transition-all duration-300 ${
                      model.available ? 'bg-green-400 shadow-lg shadow-green-400/50' : 'bg-red-400'
                    }`} />
                  </div>
                  {model.name === currentModel && (
                    <div className="text-xs text-primary font-medium animate-shimmer bg-primary/20 rounded-full px-2 py-1 text-center">
                      Active Model
                    </div>
                  )}
                  {!model.available && (
                    <div className="text-xs text-red-400 font-medium">
                      Not configured
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="glass-card">
              <div className="flex items-center space-x-3 mb-6">
                <div className="p-2 bg-primary/20 rounded-xl">
                  <Key className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-text">API Configuration</h3>
                  <p className="text-text-secondary text-sm">Connect your AI services</p>
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-text mb-2">
                    Gemini API Key
                  </label>
                  <input
                    type="password"
                    value={apiKeys.gemini}
                    onChange={(e) => setApiKeys({ ...apiKeys, gemini: e.target.value })}
                    placeholder="Enter your Gemini API key"
                    className="glass-input w-full"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-text mb-2">
                    OpenAI API Key
                  </label>
                  <input
                    type="password"
                    value={apiKeys.openai}
                    onChange={(e) => setApiKeys({ ...apiKeys, openai: e.target.value })}
                    placeholder="Enter your OpenAI API key"
                    className="glass-input w-full"
                  />
                </div>
              </div>
            </div>

            <div className="glass-card">
              <div className="flex items-center space-x-3 mb-6">
                <div className="p-2 bg-secondary/20 rounded-xl">
                  <Database className="w-5 h-5 text-secondary" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-text">Memory Management</h3>
                  <p className="text-text-secondary text-sm">Control conversation storage</p>
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-text mb-2">
                    Max Memories ({settings.maxMemories})
                  </label>
                  <input
                    type="range"
                    min="100"
                    max="10000"
                    step="100"
                    value={settings.maxMemories}
                    onChange={(e) => setSettings({ ...settings, maxMemories: parseInt(e.target.value) })}
                    className="w-full h-2 bg-surface-glass rounded-lg appearance-none cursor-pointer slider"
                  />
                  <div className="flex justify-between text-xs text-text-muted mt-1">
                    <span>100</span>
                    <span>10,000</span>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-text mb-2">
                    Memory Decay ({settings.memoryDecayDays} days)
                  </label>
                  <input
                    type="range"
                    min="30"
                    max="365"
                    value={settings.memoryDecayDays}
                    onChange={(e) => setSettings({ ...settings, memoryDecayDays: parseInt(e.target.value) })}
                    className="w-full h-2 bg-surface-glass rounded-lg appearance-none cursor-pointer slider"
                  />
                  <div className="flex justify-between text-xs text-text-muted mt-1">
                    <span>30 days</span>
                    <span>1 year</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="glass-card">
              <div className="flex items-center space-x-3 mb-6">
                <div className="p-2 bg-accent/20 rounded-xl">
                  <Brain className="w-5 h-5 text-accent" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-text">AI Reasoning</h3>
                  <p className="text-text-secondary text-sm">Configure thinking patterns</p>
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between p-3 bg-surface-glass rounded-xl">
                  <div>
                    <span className="text-sm font-medium text-text">Chain-of-Thought</span>
                    <p className="text-text-secondary text-xs">Enable step-by-step reasoning</p>
                  </div>
                  <button
                    onClick={() => setSettings({ ...settings, enableCoT: !settings.enableCoT })}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 ${
                      settings.enableCoT ? 'bg-primary' : 'bg-surface-glass'
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform duration-200 ${
                        settings.enableCoT ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>

                <div>
                  <label className="block text-sm font-medium text-text mb-2">
                    Max Reasoning Steps ({settings.maxReasoningSteps})
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="10"
                    value={settings.maxReasoningSteps}
                    onChange={(e) => setSettings({ ...settings, maxReasoningSteps: parseInt(e.target.value) })}
                    className="w-full h-2 bg-surface-glass rounded-lg appearance-none cursor-pointer slider"
                  />
                  <div className="flex justify-between text-xs text-text-muted mt-1">
                    <span>1</span>
                    <span>10</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="glass-card">
              <div className="flex items-center space-x-3 mb-6">
                <div className="p-2 bg-primary/20 rounded-xl">
                  <Shield className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-text">Data Management</h3>
                  <p className="text-text-secondary text-sm">Import, export, and manage data</p>
                </div>
              </div>

              <div className="space-y-3">
                <button
                  onClick={handleExport}
                  className="w-full btn-glass-primary flex items-center justify-center space-x-2 py-3"
                >
                  <Download className="w-5 h-5" />
                  <span>Export Memories</span>
                </button>

                <button
                  onClick={handleClearMemories}
                  className="w-full bg-red-500/20 hover:bg-red-500/30 text-red-400 hover:text-red-300 border border-red-500/30 rounded-xl flex items-center justify-center space-x-2 py-3 transition-all duration-200"
                >
                  <Trash2 className="w-5 h-5" />
                  <span>Clear All Memories</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-end space-x-3 p-6 border-t border-border-glass">
          <button
            onClick={onClose}
            className="btn-glass-secondary px-6 py-2"
          >
            Cancel
          </button>
          <button className="btn-glass-primary px-6 py-2">
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
}

export default SettingsPanel;
