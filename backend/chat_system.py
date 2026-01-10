"""
Chat System

Multi-channel MUD-style chat interface for D&D gameplay.
Supports public transcript, private messages, DM commands, and turn coordination.

Key Features:
- Multiple chat channels (public, private, system, DM)
- Real-time message routing
- Turn-based coordination
- Message formatting (MUD-style)
- Chat history and logging
- DM command interface
- Transcript generation
"""

import time
import asyncio
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of chat messages"""
    PUBLIC = "public"           # Everyone sees
    PRIVATE = "private"         # 1-to-1 message
    WHISPER = "whisper"        # Private in-character
    PARTY = "party"            # Party-only chat
    SYSTEM = "system"          # System notifications
    DM = "dm"                  # DM channel
    ACTION = "action"          # Character actions (/me)
    EMOTE = "emote"            # Emotes (*emote*)
    OOC = "ooc"                # Out of character ((text))
    ROLL = "roll"              # Dice rolls
    COMBAT = "combat"          # Combat announcements


class MessagePriority(Enum):
    """Message priority levels"""
    LOW = 1
    NORMAL = 5
    HIGH = 8
    URGENT = 10


@dataclass
class ChatMessage:
    """A single chat message"""
    message_id: str
    channel: MessageType
    sender_id: str
    sender_name: str
    content: str
    
    # Recipients
    recipient_ids: List[str] = field(default_factory=list)  # Empty = broadcast
    
    # Metadata
    timestamp: float = field(default_factory=time.time)
    priority: MessagePriority = MessagePriority.NORMAL
    turn_number: Optional[int] = None
    
    # Formatting
    color: Optional[str] = None
    style: Optional[str] = None
    
    # State
    delivered: bool = False
    read_by: Set[str] = field(default_factory=set)


@dataclass
class ChatChannel:
    """A chat channel with subscribers"""
    channel_id: str
    name: str
    channel_type: MessageType
    
    # Participants
    subscribers: Set[str] = field(default_factory=set)
    muted_users: Set[str] = field(default_factory=set)
    
    # Settings
    dm_can_read: bool = True
    allow_anonymous: bool = False
    log_messages: bool = True
    
    # History
    messages: List[ChatMessage] = field(default_factory=list)
    max_history: int = 1000


@dataclass
class ChatParticipant:
    """A participant in the chat system"""
    participant_id: str
    name: str
    role: str  # "player", "dm", "npc", "system"
    
    # Channels
    subscribed_channels: Set[str] = field(default_factory=set)
    muted_channels: Set[str] = field(default_factory=set)
    
    # State
    is_online: bool = True
    is_typing: bool = False
    last_seen: float = field(default_factory=time.time)
    
    # Preferences
    message_filter: Optional[List[MessageType]] = None
    color_scheme: str = "default"


class ChatSystem:
    """
    Multi-channel chat system for D&D gameplay
    
    Manages all chat communication including public chat, private messages,
    DM channel, and system notifications. Provides MUD-style formatting
    and turn-based coordination.
    """
    
    def __init__(self):
        """Initialize chat system"""
        # Channels
        self.channels: Dict[str, ChatChannel] = {}
        
        # Participants
        self.participants: Dict[str, ChatParticipant] = {}
        
        # Message queue
        self.message_queue: asyncio.Queue = asyncio.Queue()
        
        # Turn coordination
        self.current_turn: Optional[str] = None
        self.turn_number: int = 0
        self.turn_actions: List[ChatMessage] = []
        
        # Transcript
        self.transcript: List[ChatMessage] = []
        self.transcript_file: Optional[str] = None
        
        # Statistics
        self.stats = {
            "total_messages": 0,
            "messages_by_type": {},
            "active_participants": 0
        }
        
        # Create default channels
        self._create_default_channels()
        
        logger.info("ChatSystem initialized")
    
    def _create_default_channels(self) -> None:
        """Create default chat channels"""
        # Public channel (everyone)
        self.create_channel(
            channel_id="public",
            name="Public",
            channel_type=MessageType.PUBLIC,
            dm_can_read=True
        )
        
        # DM channel
        self.create_channel(
            channel_id="dm",
            name="DM",
            channel_type=MessageType.DM,
            dm_can_read=True
        )
        
        # System channel
        self.create_channel(
            channel_id="system",
            name="System",
            channel_type=MessageType.SYSTEM,
            dm_can_read=True
        )
        
        # Combat channel
        self.create_channel(
            channel_id="combat",
            name="Combat",
            channel_type=MessageType.COMBAT,
            dm_can_read=True
        )
    
    def create_channel(
        self,
        channel_id: str,
        name: str,
        channel_type: MessageType,
        dm_can_read: bool = True
    ) -> ChatChannel:
        """Create a new chat channel"""
        channel = ChatChannel(
            channel_id=channel_id,
            name=name,
            channel_type=channel_type,
            dm_can_read=dm_can_read
        )
        
        self.channels[channel_id] = channel
        logger.info(f"Created channel: {name} ({channel_type.value})")
        
        return channel
    
    def add_participant(
        self,
        participant_id: str,
        name: str,
        role: str = "player"
    ) -> ChatParticipant:
        """Add a participant to the chat system"""
        participant = ChatParticipant(
            participant_id=participant_id,
            name=name,
            role=role
        )
        
        self.participants[participant_id] = participant
        
        # Auto-subscribe to public and system channels
        self.subscribe_to_channel(participant_id, "public")
        self.subscribe_to_channel(participant_id, "system")
        
        if role == "dm":
            self.subscribe_to_channel(participant_id, "dm")
        
        logger.info(f"Added participant: {name} ({role})")
        
        return participant
    
    def subscribe_to_channel(
        self,
        participant_id: str,
        channel_id: str
    ) -> bool:
        """Subscribe a participant to a channel"""
        if participant_id not in self.participants:
            logger.warning(f"Participant {participant_id} not found")
            return False
        
        if channel_id not in self.channels:
            logger.warning(f"Channel {channel_id} not found")
            return False
        
        participant = self.participants[participant_id]
        channel = self.channels[channel_id]
        
        participant.subscribed_channels.add(channel_id)
        channel.subscribers.add(participant_id)
        
        logger.debug(f"{participant.name} subscribed to {channel.name}")
        return True
    
    async def send_message(
        self,
        sender_id: str,
        content: str,
        channel: MessageType = MessageType.PUBLIC,
        recipient_ids: Optional[List[str]] = None,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> Optional[ChatMessage]:
        """
        Send a chat message
        
        Args:
            sender_id: ID of sender
            content: Message content
            channel: Message type/channel
            recipient_ids: Specific recipients (None = broadcast)
            priority: Message priority
            
        Returns:
            ChatMessage if sent, None if failed
        """
        # Validate sender
        if sender_id not in self.participants:
            logger.warning(f"Unknown sender: {sender_id}")
            return None
        
        sender = self.participants[sender_id]
        
        # Create message
        message = ChatMessage(
            message_id=f"msg_{time.time()}_{sender_id}",
            channel=channel,
            sender_id=sender_id,
            sender_name=sender.name,
            content=content,
            recipient_ids=recipient_ids or [],
            timestamp=time.time(),
            priority=priority,
            turn_number=self.turn_number if self.current_turn else None
        )
        
        # Format message
        self._format_message(message, sender)
        
        # Queue for delivery
        await self.message_queue.put(message)
        
        # Update stats
        self.stats["total_messages"] += 1
        channel_key = channel.value
        self.stats["messages_by_type"][channel_key] = \
            self.stats["messages_by_type"].get(channel_key, 0) + 1
        
        logger.debug(
            f"{sender.name} sent {channel.value} message: {content[:50]}"
        )
        
        return message
    
    def _format_message(
        self,
        message: ChatMessage,
        sender: ChatParticipant
    ) -> None:
        """Apply MUD-style formatting to message"""
        
        # Color codes for different message types
        colors = {
            MessageType.PUBLIC: "white",
            MessageType.PRIVATE: "cyan",
            MessageType.WHISPER: "magenta",
            MessageType.PARTY: "yellow",
            MessageType.SYSTEM: "green",
            MessageType.DM: "red",
            MessageType.ACTION: "blue",
            MessageType.EMOTE: "pink",
            MessageType.OOC: "gray",
            MessageType.ROLL: "orange",
            MessageType.COMBAT: "red"
        }
        
        message.color = colors.get(message.channel, "white")
        
        # Style formatting
        if message.channel == MessageType.ACTION:
            message.content = f"* {sender.name} {message.content}"
        elif message.channel == MessageType.EMOTE:
            message.content = f"*{message.content}*"
        elif message.channel == MessageType.OOC:
            message.content = f"(({message.content}))"
        elif message.channel == MessageType.WHISPER:
            message.content = f"[Whisper] {sender.name}: {message.content}"
    
    async def process_messages(self) -> None:
        """Process messages from the queue and deliver them"""
        while True:
            try:
                message = await asyncio.wait_for(
                    self.message_queue.get(),
                    timeout=0.1
                )
                
                await self._deliver_message(message)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing messages: {e}")
    
    async def _deliver_message(self, message: ChatMessage) -> None:
        """Deliver a message to recipients"""
        
        # Determine recipients
        if message.recipient_ids:
            # Specific recipients
            recipients = message.recipient_ids
        else:
            # Broadcast to channel subscribers
            channel_id = self._get_channel_for_type(message.channel)
            if channel_id and channel_id in self.channels:
                recipients = list(self.channels[channel_id].subscribers)
            else:
                recipients = []
        
        # Add to channel history
        channel_id = self._get_channel_for_type(message.channel)
        if channel_id and channel_id in self.channels:
            channel = self.channels[channel_id]
            channel.messages.append(message)
            
            # Trim history if needed
            if len(channel.messages) > channel.max_history:
                channel.messages = channel.messages[-channel.max_history:]
        
        # Add to transcript (public messages only)
        if message.channel in [MessageType.PUBLIC, MessageType.ACTION, 
                              MessageType.ROLL, MessageType.COMBAT]:
            self.transcript.append(message)
            
            # Write to transcript file if enabled
            if self.transcript_file:
                self._write_to_transcript(message)
        
        # Mark as delivered
        message.delivered = True
        
        logger.debug(
            f"Delivered {message.channel.value} message to "
            f"{len(recipients)} recipients"
        )
    
    def _get_channel_for_type(self, msg_type: MessageType) -> Optional[str]:
        """Get channel ID for a message type"""
        type_to_channel = {
            MessageType.PUBLIC: "public",
            MessageType.DM: "dm",
            MessageType.SYSTEM: "system",
            MessageType.COMBAT: "combat",
            MessageType.ACTION: "public",
            MessageType.EMOTE: "public",
            MessageType.ROLL: "public"
        }
        
        return type_to_channel.get(msg_type)
    
    def get_messages(
        self,
        participant_id: str,
        channel_id: Optional[str] = None,
        since: Optional[float] = None,
        limit: int = 100
    ) -> List[ChatMessage]:
        """
        Get messages for a participant
        
        Args:
            participant_id: Participant to get messages for
            channel_id: Specific channel (None = all subscribed)
            since: Only messages after this timestamp
            limit: Maximum messages to return
            
        Returns:
            List of messages
        """
        if participant_id not in self.participants:
            return []
        
        participant = self.participants[participant_id]
        messages = []
        
        # Get channels to check
        if channel_id:
            channels = [channel_id] if channel_id in self.channels else []
        else:
            channels = list(participant.subscribed_channels)
        
        # Collect messages from channels
        for ch_id in channels:
            if ch_id not in self.channels:
                continue
            
            channel = self.channels[ch_id]
            
            for msg in channel.messages:
                # Filter by time
                if since and msg.timestamp < since:
                    continue
                
                # Check if message is for this participant
                if msg.recipient_ids and participant_id not in msg.recipient_ids:
                    continue
                
                messages.append(msg)
        
        # Sort by timestamp
        messages.sort(key=lambda m: m.timestamp)
        
        # Apply limit
        if len(messages) > limit:
            messages = messages[-limit:]
        
        return messages
    
    def start_turn(self, character_id: str) -> None:
        """Start a new turn for a character"""
        self.current_turn = character_id
        self.turn_number += 1
        self.turn_actions = []
        
        # Send system message
        asyncio.create_task(
            self.send_message(
                sender_id="system",
                content=f"Turn {self.turn_number}: {self._get_name(character_id)}'s turn",
                channel=MessageType.SYSTEM,
                priority=MessagePriority.HIGH
            )
        )
        
        logger.info(f"Turn {self.turn_number} started for {character_id}")
    
    def end_turn(self) -> None:
        """End the current turn"""
        if self.current_turn:
            char_name = self._get_name(self.current_turn)
            
            # Send system message
            asyncio.create_task(
                self.send_message(
                    sender_id="system",
                    content=f"{char_name}'s turn ended",
                    channel=MessageType.SYSTEM
                )
            )
            
            self.current_turn = None
    
    def _get_name(self, participant_id: str) -> str:
        """Get name of participant"""
        if participant_id in self.participants:
            return self.participants[participant_id].name
        return participant_id
    
    def enable_transcript(self, filepath: str) -> None:
        """Enable transcript logging to file"""
        self.transcript_file = filepath
        logger.info(f"Transcript logging enabled: {filepath}")
    
    def _write_to_transcript(self, message: ChatMessage) -> None:
        """Write a message to the transcript file"""
        if not self.transcript_file:
            return
        
        try:
            timestamp = datetime.fromtimestamp(message.timestamp)
            line = f"[{timestamp:%H:%M:%S}] {message.sender_name}: {message.content}\n"
            
            with open(self.transcript_file, 'a') as f:
                f.write(line)
        except Exception as e:
            logger.error(f"Error writing to transcript: {e}")
    
    def get_transcript(
        self,
        since: Optional[float] = None,
        format: str = "text"
    ) -> str:
        """
        Get the game transcript
        
        Args:
            since: Only messages after this timestamp
            format: "text" or "json"
            
        Returns:
            Formatted transcript
        """
        messages = self.transcript
        
        if since:
            messages = [m for m in messages if m.timestamp >= since]
        
        if format == "json":
            return json.dumps([{
                "timestamp": m.timestamp,
                "sender": m.sender_name,
                "content": m.content,
                "type": m.channel.value
            } for m in messages], indent=2)
        
        else:  # text
            lines = []
            for msg in messages:
                timestamp = datetime.fromtimestamp(msg.timestamp)
                lines.append(f"[{timestamp:%H:%M:%S}] {msg.sender_name}: {msg.content}")
            
            return "\n".join(lines)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get chat statistics"""
        return {
            **self.stats,
            "active_participants": sum(
                1 for p in self.participants.values() if p.is_online
            ),
            "total_channels": len(self.channels),
            "transcript_length": len(self.transcript)
        }


# Test code
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    async def test_chat_system():
        print("Testing Chat System...\n")
        
        # Create chat system
        chat = ChatSystem()
        
        # Add participants
        print("=== Test 1: Adding Participants ===")
        chat.add_participant("dm1", "Dungeon Master", role="dm")
        chat.add_participant("player1", "Thorin", role="player")
        chat.add_participant("player2", "Elara", role="player")
        print(f"Participants: {len(chat.participants)}")
        print()
        
        # Start message processing
        asyncio.create_task(chat.process_messages())
        
        # Test public message
        print("=== Test 2: Public Message ===")
        await chat.send_message(
            sender_id="player1",
            content="I search the room for traps.",
            channel=MessageType.PUBLIC
        )
        await asyncio.sleep(0.1)
        
        messages = chat.get_messages("player2", channel_id="public")
        print(f"Player2 sees {len(messages)} message(s)")
        if messages:
            print(f"Content: {messages[0].content}")
        print()
        
        # Test private message
        print("=== Test 3: Private Message ===")
        await chat.send_message(
            sender_id="player1",
            content="Should we attack the dragon?",
            channel=MessageType.PRIVATE,
            recipient_ids=["player2"]
        )
        await asyncio.sleep(0.1)
        
        private_msgs = chat.get_messages("player2")
        print(f"Player2 has {len(private_msgs)} total message(s)")
        print()
        
        # Test turn coordination
        print("=== Test 4: Turn Coordination ===")
        chat.start_turn("player1")
        await asyncio.sleep(0.1)
        
        await chat.send_message(
            sender_id="player1",
            content="attacks with sword!",
            channel=MessageType.ACTION
        )
        await asyncio.sleep(0.1)
        
        chat.end_turn()
        await asyncio.sleep(0.1)
        
        print(f"Current turn: {chat.current_turn}")
        print(f"Turn number: {chat.turn_number}")
        print()
        
        # Test transcript
        print("=== Test 5: Transcript ===")
        chat.enable_transcript("/tmp/test_transcript.txt")
        
        await chat.send_message(
            sender_id="dm1",
            content="The orc roars and charges!",
            channel=MessageType.PUBLIC
        )
        await asyncio.sleep(0.1)
        
        transcript = chat.get_transcript()
        print("Transcript:")
        print(transcript)
        print()
        
        # Test statistics
        print("=== Test 6: Statistics ===")
        stats = chat.get_stats()
        print(f"Stats: {stats}")
        print()
        
        print("✅ All chat system tests completed!")
    
    asyncio.run(test_chat_system())
