from flask_socketio import SocketIO, emit, join_room, leave_room
from flask import request
from datetime import datetime
import json

class WebSocketService:
    def __init__(self, app, redis_client, logger):
        self.app = app
        self.redis_client = redis_client
        self.logger = logger
        self.socketio = SocketIO(
            app,
            cors_allowed_origins=["https://datinglanguage.onrender.com", "http://localhost:5000"],
            async_mode='threading',  # Use threading for Render compatibility
            ping_timeout=60,
            ping_interval=25
        )
        self.setup_handlers()
    
    def setup_handlers(self):
        @self.socketio.on('connect')
        def handle_connect(auth):
            try:
                # Basic connection - improve authentication later
                user_id = request.sid  # Use session ID for now
                join_room(f"user_{user_id}")
                emit('connection_established', {'status': 'connected'})
                self.logger.info(f"WebSocket connected: {user_id}")
                return True
            except Exception as e:
                self.logger.error(f"Connection failed: {e}")
                return False
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            self.logger.info(f"WebSocket disconnected: {request.sid}")
    
    def notify_new_match(self, user_id, match_data):
        try:
            room = f"user_{user_id}"
            self.socketio.emit('new_match', {
                'type': 'new_match',
                'data': match_data,
                'timestamp': datetime.utcnow().isoformat()
            }, room=room)
        except Exception as e:
            self.logger.error(f"Failed to send match notification: {e}")
    
    def run(self, host='0.0.0.0', port=5000, debug=False):
        self.socketio.run(self.app, host=host, port=port, debug=debug)
