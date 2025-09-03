// WebSocket Service Module for Table for Two
// Handles real-time communication with automatic reconnection

class WebSocketService {
    constructor() {
        this.ws = null;
        this.reconnectInterval = 5000;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.handlers = new Map();
        this.isIntentionallyClosed = false;
    }

    // Connect to WebSocket server
    connect() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            console.log('WebSocket already connected');
            return;
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl
