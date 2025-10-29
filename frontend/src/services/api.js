import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const sendMessage = async (message, model = null, enableReasoning = true, sessionId = null) => {
  const response = await api.post('/api/chat/', {
    message,
    model,
    enable_reasoning: enableReasoning,
    session_id: sessionId,
  });
  return response.data;
};

export const sendMessageWithTaskPlanning = async (message, model = null, sessionId = null) => {
  const response = await api.post('/api/chat/task-plan', {
    message,
    model,
    session_id: sessionId,
  });
  return response.data;
};

export const getMemories = async (skip = 0, limit = 50, memoryType = null) => {
  const params = { skip, limit };
  if (memoryType) params.memory_type = memoryType;
  
  const response = await api.get('/api/memory/', { params });
  return response.data;
};

export const createMemory = async (content, memoryType, importance = 1.0, metadata = {}) => {
  const response = await api.post('/api/memory/', {
    content,
    memory_type: memoryType,
    importance,
    metadata,
  });
  return response.data;
};

export const searchMemories = async (query, k = 5, memoryType = null, sessionId = null) => {
  const response = await api.post('/api/memory/search', {
    query,
    k,
    memory_type: memoryType,
    session_id: sessionId,
  });
  return response.data;
};

export const getMemoryStats = async () => {
  const response = await api.get('/api/memory/stats');
  return response.data;
};

export const deleteMemory = async (memoryIndex) => {
  const response = await api.delete(`/api/memory/${memoryIndex}`);
  return response.data;
};

export const clearAllMemories = async () => {
  const response = await api.delete('/api/memory/');
  return response.data;
};

export const exportMemories = async () => {
  const response = await api.post('/api/memory/export');
  return response.data;
};

export const getModels = async () => {
  const response = await api.get('/api/models/');
  return response.data;
};

export const switchModel = async (model) => {
  const response = await api.post('/api/models/switch', { model });
  return response.data;
};

export const getModelsStatus = async () => {
  const response = await api.get('/api/models/status');
  return response.data;
};

export const getCurrentModel = async () => {
  const response = await api.get('/api/models/current');
  return response.data;
};

export const getHealth = async () => {
  const response = await api.get('/api/health');
  return response.data;
};

export default api;
