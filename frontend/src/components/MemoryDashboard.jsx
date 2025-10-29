import React, { useState, useEffect, useMemo } from 'react';
import { Database, TrendingUp, Calendar, Trash2, Search, Filter, RefreshCw, Download, Layers, ChevronDown } from 'lucide-react';
import { getMemories, getMemoryStats, deleteMemory, searchMemories, clearAllMemories, exportMemories } from '../services/api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';

const COLORS = {
  'user_info': '#0ea5e9',
  'conversation': '#8b5cf6',
  'knowledge': '#10b981',
  'preference': '#f59e0b',
};

function MemoryDashboard() {
  const [memories, setMemories] = useState([]);
  const [stats, setStats] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState('all');
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview'); // overview | browse | search | actions
  const [searchResults, setSearchResults] = useState([]);
  const [searchK, setSearchK] = useState(10);
  const [sortBy, setSortBy] = useState('time_desc');
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [skip, setSkip] = useState(0);
  const [pageSize] = useState(200);
  const [hasMore, setHasMore] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const [memoriesData, statsData] = await Promise.all([
        getMemories(0, pageSize),
        getMemoryStats(),
      ]);
      // attach originalIndex based on backend index (skip + i)
      const withIndex = (memoriesData || []).map((m, i) => ({ ...m, originalIndex: i }));
      setMemories(withIndex);
      setSkip(withIndex.length);
      setHasMore((memoriesData || []).length === pageSize);
      setStats(statsData);
    } catch (error) {
      console.error('Error fetching memory data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadMore = async () => {
    if (isLoadingMore || !hasMore) return;
    setIsLoadingMore(true);
    try {
      const more = await getMemories(skip, pageSize);
      const mapped = (more || []).map((m, i) => ({ ...m, originalIndex: skip + i }));
      setMemories(prev => [...prev, ...mapped]);
      const newSkip = skip + mapped.length;
      setSkip(newSkip);
      setHasMore((more || []).length === pageSize);
    } catch (e) {
      console.error('Error loading more memories:', e);
    } finally {
      setIsLoadingMore(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }

    try {
      const results = await searchMemories(searchQuery, searchK);
      setSearchResults(results || []);
    } catch (error) {
      console.error('Error searching memories:', error);
    }
  };

  const handleDelete = async (originalIndex) => {
    if (window.confirm('Are you sure you want to delete this memory?')) {
      try {
        await deleteMemory(originalIndex);
        fetchData();
      } catch (error) {
        console.error('Error deleting memory:', error);
      }
    }
  };

  const filteredMemories = useMemo(() => {
    const base = selectedType === 'all' ? memories : memories.filter(m => m.memory_type === selectedType);
    return base;
  }, [memories, selectedType]);

  const browseMemories = useMemo(() => {
    let list = filteredMemories;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(m =>
        (m.content || '').toLowerCase().includes(q)
        || (m.memory_type || '').toLowerCase().includes(q)
      );
    }
    // sorting
    const sorted = [...list].sort((a, b) => {
      switch (sortBy) {
        case 'time_asc':
          return new Date(a.timestamp) - new Date(b.timestamp);
        case 'importance_desc':
          return (b.importance || 0) - (a.importance || 0);
        case 'access_desc':
          return (b.access_count || 0) - (a.access_count || 0);
        case 'time_desc':
        default:
          return new Date(b.timestamp) - new Date(a.timestamp);
      }
    });
    return sorted;
  }, [filteredMemories, searchQuery, sortBy]);

  const typeData = stats?.by_type
    ? Object.entries(stats.by_type).map(([name, value]) => ({ name, value }))
    : [];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="glass-card p-8 text-center">
          <div className="animate-shimmer w-8 h-8 bg-surface-glass rounded-full mx-auto mb-4"></div>
          <p className="text-text-secondary">Loading memory data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Tabs */}
      <div className="flex items-center gap-2">
        {[
          { id: 'overview', label: 'Overview' },
          { id: 'browse', label: 'Browse' },
          { id: 'search', label: 'Search' },
          { id: 'actions', label: 'Actions' },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded-xl transition-all duration-200 glass-hover ${
              activeTab === tab.id ? 'bg-primary/20 text-primary shadow-md' : 'text-text-secondary hover:bg-surface-glass'
            }`}
          >
            {tab.label}
          </button>
        ))}
        <button onClick={fetchData} className="ml-auto btn-glass-secondary flex items-center gap-2 px-3 py-2">
          <RefreshCw size={16} />
          <span>Refresh</span>
        </button>
      </div>
      <div className="flex flex-wrap items-center gap-3 text-xs text-text-secondary">
        {Object.entries(COLORS).map(([type, color]) => (
          <span key={type} className="inline-flex items-center gap-2">
            <span className="w-3 h-3 rounded-full" style={{ backgroundColor: color }}></span>
            <button
              className={`hover:text-text transition-colors ${selectedType === type ? 'text-text' : ''}`}
              onClick={() => setSelectedType(prev => prev === type ? 'all' : type)}
            >
              {type}
            </button>
          </span>
        ))}
        {selectedType !== 'all' && (
          <button onClick={() => setSelectedType('all')} className="ml-2 text-text-secondary underline hover:text-text">
            Clear filter
          </button>
        )}
      </div>
      {/* Overview */}
      {activeTab === 'overview' && (
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="glass-card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-text-secondary mb-1">Total Memories</p>
              <p className="text-2xl font-bold text-text">{stats?.total_memories || 0}</p>
            </div>
            <div className="avatar glow-primary">
              <Database className="w-6 h-6 text-primary" />
            </div>
          </div>
        </div>

        <div className="glass-card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-text-secondary mb-1">Avg Age (days)</p>
              <p className="text-2xl font-bold text-text">
                {stats?.avg_age_days ? Math.round(stats.avg_age_days) : 0}
              </p>
            </div>
            <div className="avatar glow-secondary">
              <Calendar className="w-6 h-6 text-secondary" />
            </div>
          </div>
        </div>

        <div className="glass-card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-text-secondary mb-1">Memory Types</p>
              <p className="text-2xl font-bold text-text">
                {stats?.by_type ? Object.keys(stats.by_type).length : 0}
              </p>
            </div>
            <div className="avatar glow-primary">
              <Filter className="w-6 h-6 text-accent" />
            </div>
          </div>
        </div>

        <div className="glass-card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-text-secondary mb-1">Most Common</p>
              <p className="text-lg font-bold text-text capitalize">
                {typeData.length > 0 ? typeData.sort((a, b) => b.value - a.value)[0].name : 'N/A'}
              </p>
            </div>
            <div className="avatar glow-secondary">
              <TrendingUp className="w-6 h-6 text-green-400" />
            </div>
          </div>
        </div>
  </div>
  )}

      {/* Charts */}
      {activeTab === 'overview' && typeData.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="glass-card p-6">
            <h3 className="text-lg font-semibold text-text mb-4">Memory Distribution</h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={typeData}
                    labelLine={false}
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {typeData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[entry.name] || '#6b7280'} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="glass-card p-6">
            <h3 className="text-lg font-semibold text-text mb-4">Memory Count by Type</h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={typeData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis dataKey="name" stroke="rgb(var(--color-text-secondary))" />
                  <YAxis stroke="rgb(var(--color-text-secondary))" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgb(var(--color-surface-solid))',
                      border: '1px solid rgb(var(--color-border-glass))',
                      borderRadius: '8px'
                    }}
                  />
                  <Bar dataKey="value" fill="rgb(var(--color-primary))" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* Browse */}
      {activeTab === 'browse' && (
      <div className="glass-card p-6">
        <div className="flex items-center flex-wrap gap-4 mb-4">
          <div className="flex-1 flex items-center space-x-3">
            <div className="relative flex-1">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search memories..."
                className="glass-input w-full pl-4 pr-12"
              />
              <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-secondary" />
            </div>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="glass-input w-44"
            >
              <option value="all">All Types</option>
              <option value="user_info">User Info</option>
              <option value="conversation">Conversation</option>
              <option value="knowledge">Knowledge</option>
              <option value="preference">Preference</option>
            </select>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="glass-input w-48"
            >
              <option value="time_desc">Newest first</option>
              <option value="time_asc">Oldest first</option>
              <option value="importance_desc">Importance (high → low)</option>
              <option value="access_desc">Access count (high → low)</option>
            </select>
          </div>
        </div>

        {selectedIds.size > 0 && (
          <div className="mb-3 flex items-center justify-between text-xs">
            <span className="text-text-secondary">Selected {selectedIds.size} item(s)</span>
            <button
              className="px-3 py-1.5 rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors"
              onClick={async () => {
                if (!window.confirm(`Delete ${selectedIds.size} selected item(s)?`)) return;
                try {
                  // delete in descending order of originalIndex to avoid reindex issues
                  const ids = Array.from(selectedIds).sort((a,b)=>b-a);
                  for (const id of ids) {
                    // eslint-disable-next-line no-await-in-loop
                    await deleteMemory(id);
                  }
                  setSelectedIds(new Set());
                  await fetchData();
                } catch (e) {
                  alert('Failed to delete selected memories');
                }
              }}
            >
              Delete Selected
            </button>
          </div>
        )}

        {/* Memories List */}
        <div className="space-y-3 max-h-96 overflow-y-auto custom-scrollbar">
          {browseMemories.length === 0 ? (
            <div className="text-center py-12">
              <div className="avatar mx-auto mb-4 opacity-50">
                <Database className="w-6 h-6" />
              </div>
              <p className="text-text-secondary">No memories found</p>
            </div>
          ) : (
            browseMemories.map((memory, index) => (
              <div
                key={index}
                className="glass-card p-4 hover:bg-surface-glass transition-colors duration-200"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-2">
                      <input
                        type="checkbox"
                        className="rounded accent-primary cursor-pointer"
                        checked={selectedIds.has(memory.originalIndex)}
                        onChange={(e) => {
                          const next = new Set(selectedIds);
                          if (e.target.checked) next.add(memory.originalIndex);
                          else next.delete(memory.originalIndex);
                          setSelectedIds(next);
                        }}
                        title="Select"
                      />
                      <span
                        className="px-3 py-1 text-xs font-medium rounded-full text-white"
                        style={{ backgroundColor: COLORS[memory.memory_type] || '#6b7280' }}
                      >
                        {memory.memory_type}
                      </span>
                      <span className="text-xs text-text-secondary">
                        {new Date(memory.timestamp).toLocaleDateString()}
                      </span>
                      <span className="text-xs text-text-muted">
                        Accessed: {memory.access_count}x
                      </span>
                      <span className="text-xs text-text-secondary inline-flex items-center gap-1">
                        <Layers size={12} /> idx {memory.originalIndex}
                      </span>
                    </div>
                    <p className="text-sm text-text mb-2">{memory.content}</p>
                    <div className="flex items-center gap-4 text-xs text-text-secondary">
                      <span>Importance: {memory.importance.toFixed(1)}</span>
                      <div className="flex items-center gap-1">
                        <div className="w-16 h-1 bg-surface-glass rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-primary to-secondary rounded-full"
                            style={{ width: `${memory.importance * 100}%` }}
                          ></div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => handleDelete(memory.originalIndex)}
                    className="ml-4 p-2 text-red-400 hover:bg-red-500/20 rounded-lg transition-colors"
                    title="Delete memory"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
        {hasMore && (
          <div className="mt-4 flex justify-center">
            <button
              className="btn-glass-secondary px-4 py-2 flex items-center gap-2 disabled:opacity-50"
              onClick={loadMore}
              disabled={isLoadingMore}
            >
              {isLoadingMore ? (
                <>
                  <RefreshCw size={16} className="animate-spin" /> Loading...
                </>
              ) : (
                <>
                  <ChevronDown size={16} /> Load more
                </>
              )}
            </button>
          </div>
        )}
      </div>
      )}

      {/* Search */}
      {activeTab === 'search' && (
        <div className="glass-card p-6">
          <div className="flex items-center gap-3 mb-4 flex-wrap">
            <div className="relative flex-1">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="Semantic search memories..."
                className="glass-input w-full pl-4 pr-12"
              />
              <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-secondary" />
            </div>
            <div className="flex items-center gap-2">
              <label className="text-xs text-text-secondary">Top K</label>
              <input type="number" min={1} max={50} value={searchK} onChange={(e)=>setSearchK(parseInt(e.target.value||'10'))} className="glass-input w-20" />
            </div>
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="glass-input w-44"
              title="Filter type"
            >
              <option value="all">All Types</option>
              <option value="user_info">User Info</option>
              <option value="conversation">Conversation</option>
              <option value="knowledge">Knowledge</option>
              <option value="preference">Preference</option>
            </select>
            <button onClick={handleSearch} className="btn-glass-primary px-4 py-2">Search</button>
          </div>
          <div className="space-y-3 max-h-96 overflow-y-auto custom-scrollbar">
            {searchResults.length === 0 ? (
              <div className="text-center py-10 text-text-secondary">No results</div>
            ) : (
              searchResults
                .filter(m => selectedType === 'all' || m.memory_type === selectedType)
                .map((m, i) => (
                <div key={i} className="glass-card p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <span
                      className="px-3 py-1 text-xs font-medium rounded-full text-white"
                      style={{ backgroundColor: COLORS[m.memory_type] || '#6b7280' }}
                    >
                      {m.memory_type}
                    </span>
                    <span className="text-xs text-text-secondary">{new Date(m.timestamp).toLocaleDateString()}</span>
                    <span className="text-xs text-text-muted">Accessed: {m.access_count}x</span>
                  </div>
                  <p className="text-sm text-text">{m.content}</p>
                </div>
              ))
            )}
          </div>
          <p className="mt-3 text-xs text-text-muted">Tip: Delete memories from the Browse tab. Search results are read-only.</p>
        </div>
      )}

      {/* Actions */}
      {activeTab === 'actions' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="glass-card p-6">
            <h3 className="text-lg font-semibold text-text mb-2">Export Memories</h3>
            <p className="text-sm text-text-secondary mb-4">Download all memories as JSON for backup or analysis.</p>
            <button
              className="btn-glass-secondary flex items-center gap-2 px-4 py-2"
              onClick={async () => {
                try {
                  const data = await exportMemories();
                  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `cognos-memories-${new Date().toISOString().slice(0,10)}.json`;
                  a.click();
                  URL.revokeObjectURL(url);
                } catch (e) {
                  alert('Failed to export memories');
                }
              }}
            >
              <Download size={16} />
              <span>Export JSON</span>
            </button>
          </div>
          <div className="glass-card p-6">
            <h3 className="text-lg font-semibold text-text mb-2">Clear All Memories</h3>
            <p className="text-sm text-text-secondary mb-4">Remove all stored memories. This cannot be undone.</p>
            <button
              className="px-4 py-2 rounded-xl bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors"
              onClick={async () => {
                if (!window.confirm('This will permanently delete all memories. Continue?')) return;
                try {
                  await clearAllMemories();
                  await fetchData();
                } catch (e) {
                  alert('Failed to clear memories');
                }
              }}
            >
              Clear All
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default MemoryDashboard;
