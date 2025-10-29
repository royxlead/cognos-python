class WebSocketService {
  constructor() {
    this.ws = null;
    this.messageHandlers = [];
    this.errorHandlers = [];
    this.connectHandlers = [];
    this.disconnectHandlers = [];
    this.isConnected = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
  }

  connect(url = null) {
    const wsUrl = url || `ws://localhost:8000/ws/chat`;
    
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.isConnected = true;
      this.reconnectAttempts = 0;
      this.connectHandlers.forEach(handler => handler());
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.messageHandlers.forEach(handler => handler(data));
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.errorHandlers.forEach(handler => handler(error));
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      this.isConnected = false;
      this.disconnectHandlers.forEach(handler => handler());
      
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        console.log(`Reconnecting... Attempt ${this.reconnectAttempts}`);
        setTimeout(() => this.connect(wsUrl), 2000 * this.reconnectAttempts);
      }
    };
  }

  sendMessage(message, enableReasoning = true) {
    if (this.ws && this.isConnected) {
      this.ws.send(JSON.stringify({
        message,
        enable_reasoning: enableReasoning,
      }));
    } else {
      console.error('WebSocket is not connected');
    }
  }

  onMessage(handler) {
    this.messageHandlers.push(handler);
  }

  onError(handler) {
    this.errorHandlers.push(handler);
  }

  onConnect(handler) {
    this.connectHandlers.push(handler);
  }

  onDisconnect(handler) {
    this.disconnectHandlers.push(handler);
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
      this.isConnected = false;
    }
  }

  removeHandlers() {
    this.messageHandlers = [];
    this.errorHandlers = [];
    this.connectHandlers = [];
    this.disconnectHandlers = [];
  }
}

export default new WebSocketService();
