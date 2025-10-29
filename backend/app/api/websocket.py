"""WebSocket endpoint for real-time chat."""
import logging
import json
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict
from app.core.llm_manager import llm_manager
from app.core.memory_manager import memory_manager
from app.core.reasoning_engine import reasoning_engine
from app.core.context_manager import context_manager

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept and store new connection."""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected")
    
    def disconnect(self, client_id: str):
        """Remove connection."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Client {client_id} disconnected")
    
    async def send_message(self, message: dict, client_id: str):
        """Send message to specific client."""
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)
    
    async def send_text(self, text: str, client_id: str):
        """Send text message to specific client."""
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(text)


manager = ConnectionManager()


@router.websocket("/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for real-time chat."""
    client_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    
    await manager.connect(websocket, client_id)
    
    try:
        # Send welcome message
        await manager.send_message({
            "type": "connected",
            "client_id": client_id,
            "session_id": session_id,
            "message": "Connected to COGNOS"
        }, client_id)
        
        while True:
            # Receive message
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
                user_message = message_data.get("message", "")
                enable_reasoning = message_data.get("enable_reasoning", True)
                
                if not user_message:
                    continue
                
                # Send thinking status
                await manager.send_message({
                    "type": "thinking",
                    "message": "Processing your request..."
                }, client_id)
                
                # Add to short-term memory
                memory_manager.add_to_short_term("user", user_message)
                
                # Get context
                context = await memory_manager.get_context(
                    user_message,
                    k=5,
                    include_short_term=True
                )
                
                # Send memory retrieval status
                memories = await memory_manager.retrieve(user_message, k=5)
                if memories:
                    await manager.send_message({
                        "type": "memories_retrieved",
                        "count": len(memories)
                    }, client_id)
                
                # Build prompt
                full_prompt = context_manager.build_prompt(
                    query=user_message,
                    context=context
                )
                
                # Generate response with reasoning
                result = await reasoning_engine.reason(
                    query=full_prompt,
                    context=context,
                    use_cot=enable_reasoning
                )
                
                # Send reasoning steps if available
                if result.get('reasoning_steps'):
                    for step in result['reasoning_steps']:
                        await manager.send_message({
                            "type": "reasoning_step",
                            "step": step
                        }, client_id)
                
                # Add assistant response to memory
                memory_manager.add_to_short_term("assistant", result['answer'])
                
                # Store conversation memory
                await memory_manager.add_memory(
                    content=f"Q: {user_message}\nA: {result['answer']}",
                    memory_type="conversation",
                    importance=1.0,
                    session_id=session_id
                )
                
                # Send final response
                await manager.send_message({
                    "type": "response",
                    "answer": result['answer'],
                    "confidence": result.get('confidence', 0.8),
                    "method": result.get('method', 'direct'),
                    "memories_used": len(memories),
                    "session_id": session_id
                }, client_id)
                
            except json.JSONDecodeError:
                await manager.send_message({
                    "type": "error",
                    "message": "Invalid JSON format"
                }, client_id)
                
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                await manager.send_message({
                    "type": "error",
                    "message": str(e)
                }, client_id)
    
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        logger.info(f"Client {client_id} disconnected")
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        manager.disconnect(client_id)
