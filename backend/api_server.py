"""
AI Society D&D - Main API Server
==================================
FastAPI server that integrates all systems:
- Character management
- Game rooms and sessions
- DM system
- Memory consolidation
- Cultural transmission
- WebSocket for real-time updates
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import asyncio
import json
from datetime import datetime

# Import our systems
from enhanced_character import EnhancedCharacter, CharacterClass, create_sample_character
from game_room import DnDGameRoom, DungeonMaster, SessionManager
from game_mechanics import CombatEncounter, SkillCheck
from memory_system import MemoryType
from cultural_transmission import CulturalTransmissionEngine, SkillPackage


# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(title="AI Society D&D", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
session_manager = SessionManager()
cultural_engine = CulturalTransmissionEngine()

# WebSocket connections
active_connections: Dict[str, WebSocket] = {}


# ============================================================================
# PYDANTIC MODELS (Request/Response)
# ============================================================================

class CreateCharacterRequest(BaseModel):
    name: str
    race: str
    class_name: str
    level: int = 1
    personality_traits: List[str]
    backstory: str
    
    # Optional stat overrides
    strength: Optional[int] = None
    dexterity: Optional[int] = None
    constitution: Optional[int] = None
    intelligence: Optional[int] = None
    wisdom: Optional[int] = None
    charisma: Optional[int] = None


class CreateCampaignRequest(BaseModel):
    campaign_name: str
    dm_id: str = "human_dm"
    initial_world_lore: Optional[List[str]] = None


class CreateSessionRequest(BaseModel):
    campaign_name: str
    session_number: int


class JoinSessionRequest(BaseModel):
    session_id: str
    character_id: str


class DMNarrateRequest(BaseModel):
    session_id: str
    narration: str


class CharacterActionRequest(BaseModel):
    session_id: str
    character_id: str
    action_description: str
    action_type: str = "roleplay"


class StartCombatRequest(BaseModel):
    session_id: str
    enemies: List[Dict[str, Any]]


class CombatActionRequest(BaseModel):
    session_id: str
    attacker_id: str
    action_type: str
    target_id: Optional[str] = None
    weapon: Optional[str] = None
    attack_bonus: int = 0
    damage_dice: str = "1d8"
    damage_bonus: int = 0


class SkillCheckRequest(BaseModel):
    character_id: str
    skill: str
    advantage: bool = False
    disadvantage: bool = False


class PrivateLLMQueryRequest(BaseModel):
    character_id: str
    query: str


# ============================================================================
# WEBSOCKET HANDLERS
# ============================================================================

@app.websocket("/ws/{session_id}/{client_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, client_id: str):
    """WebSocket connection for real-time game updates"""
    await websocket.accept()
    active_connections[client_id] = websocket
    
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages (future: player actions, dice rolls, etc.)
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        del active_connections[client_id]


async def broadcast_to_session(session_id: str, message: Dict):
    """Broadcast message to all connected clients in a session"""
    disconnected = []
    for client_id, connection in active_connections.items():
        try:
            await connection.send_json(message)
        except:
            disconnected.append(client_id)
    
    # Clean up disconnected clients
    for client_id in disconnected:
        del active_connections[client_id]


# ============================================================================
# CHARACTER ENDPOINTS
# ============================================================================

@app.post("/characters/create")
async def create_character(request: CreateCharacterRequest):
    """Create a new character"""
    try:
        # Create character class
        char_class = CharacterClass(
            name=request.class_name,
            level=request.level
        )
        
        # Generate character ID
        import hashlib
        char_id = hashlib.md5(f"{request.name}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        # Create character
        character = EnhancedCharacter(
            character_id=char_id,
            name=request.name,
            race=request.race,
            character_class=char_class,
            personality_traits=request.personality_traits,
            backstory=request.backstory
        )
        
        # Override stats if provided
        if request.strength:
            character.stats.strength = request.strength
        if request.dexterity:
            character.stats.dexterity = request.dexterity
        if request.constitution:
            character.stats.constitution = request.constitution
        if request.intelligence:
            character.stats.intelligence = request.intelligence
        if request.wisdom:
            character.stats.wisdom = request.wisdom
        if request.charisma:
            character.stats.charisma = request.charisma
        
        # Register character
        session_manager.register_character(character)
        
        return {
            "success": True,
            "character_id": char_id,
            "character": character.get_character_sheet()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/characters/{character_id}")
async def get_character(character_id: str):
    """Get character details"""
    character = session_manager.get_character(character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    return character.get_character_sheet()


@app.get("/characters/{character_id}/memories")
async def get_character_memories(character_id: str, limit: int = 20):
    """Get character's memories"""
    character = session_manager.get_character(character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    memories = list(character.memory_engine.memories.values())[-limit:]
    
    return {
        "character_id": character_id,
        "total_memories": len(character.memory_engine.memories),
        "recent_memories": [m.to_dict() for m in memories]
    }


@app.get("/characters/{character_id}/journal")
async def get_character_journal(character_id: str):
    """Get character's journal entries"""
    character = session_manager.get_character(character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    return {
        "character_id": character_id,
        "journal_entries": character.laptop.journal_entries
    }


@app.post("/characters/{character_id}/private_query")
async def character_private_query(character_id: str, request: PrivateLLMQueryRequest):
    """Character makes a private LLM query"""
    character = session_manager.get_character(character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    response = await character.laptop.private_llm_query(request.query)
    
    return {
        "query": request.query,
        "response": response,
        "visible_to_dm": character.laptop.dm_can_see_private_calls
    }


@app.post("/characters/{character_id}/skill_check")
async def make_skill_check(character_id: str, request: SkillCheckRequest):
    """Make a skill check"""
    character = session_manager.get_character(character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    # Get ability scores as dict
    ability_scores = {
        "strength": character.stats.strength,
        "dexterity": character.stats.dexterity,
        "constitution": character.stats.constitution,
        "intelligence": character.stats.intelligence,
        "wisdom": character.stats.wisdom,
        "charisma": character.stats.charisma
    }
    
    result = SkillCheck.make_check(
        skill=request.skill,
        ability_scores=ability_scores,
        proficiency_bonus=character.character_class.proficiency_bonus,
        is_proficient=True,  # Would track proficiencies
        advantage=request.advantage,
        disadvantage=request.disadvantage
    )
    
    return result


# ============================================================================
# CAMPAIGN ENDPOINTS
# ============================================================================

@app.post("/campaigns/create")
async def create_campaign(request: CreateCampaignRequest):
    """Create a new campaign"""
    try:
        dm = session_manager.create_campaign(
            campaign_name=request.campaign_name,
            dm_id=request.dm_id
        )
        
        # Add initial world lore
        if request.initial_world_lore:
            for lore in request.initial_world_lore:
                dm.add_world_lore(lore)
        
        return {
            "success": True,
            "campaign_name": request.campaign_name,
            "stats": dm.get_campaign_stats()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/campaigns/{campaign_name}")
async def get_campaign(campaign_name: str):
    """Get campaign details"""
    dm = session_manager.get_campaign(campaign_name)
    if not dm:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    return dm.get_campaign_stats()


@app.post("/campaigns/{campaign_name}/lore")
async def add_world_lore(campaign_name: str, lore_entry: str, category: str = "general"):
    """Add world lore to campaign"""
    dm = session_manager.get_campaign(campaign_name)
    if not dm:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    dm.add_world_lore(lore_entry, category)
    
    return {"success": True, "lore_entry": lore_entry}


@app.get("/campaigns/{campaign_name}/lore")
async def query_world_lore(campaign_name: str, query: str):
    """Query world lore"""
    dm = session_manager.get_campaign(campaign_name)
    if not dm:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    results = dm.query_world_lore(query)
    
    return {
        "query": query,
        "results": results
    }


# ============================================================================
# SESSION ENDPOINTS
# ============================================================================

@app.post("/sessions/create")
async def create_session(request: CreateSessionRequest):
    """Create a new game session"""
    dm = session_manager.get_campaign(request.campaign_name)
    if not dm:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    room = dm.create_session(request.session_number)
    
    return {
        "success": True,
        "session_id": room.room_id,
        "campaign_name": room.campaign_name,
        "session_number": room.session_number
    }


@app.post("/sessions/join")
async def join_session(request: JoinSessionRequest):
    """Add character to session"""
    # Find the session
    for campaign_name, dm in session_manager.campaigns.items():
        if request.session_id in dm.active_sessions:
            room = dm.active_sessions[request.session_id]
            character = session_manager.get_character(request.character_id)
            
            if not character:
                raise HTTPException(status_code=404, detail="Character not found")
            
            room.add_character(character)
            
            # Broadcast to session
            await broadcast_to_session(request.session_id, {
                "type": "character_joined",
                "character": character.name,
                "character_id": request.character_id
            })
            
            return {
                "success": True,
                "session_id": request.session_id,
                "character": character.name
            }
    
    raise HTTPException(status_code=404, detail="Session not found")


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session details"""
    for campaign_name, dm in session_manager.campaigns.items():
        if session_id in dm.active_sessions:
            room = dm.active_sessions[session_id]
            
            return {
                "session_id": room.room_id,
                "campaign_name": room.campaign_name,
                "session_number": room.session_number,
                "phase": room.game_state.phase.value,
                "location": room.game_state.current_location,
                "characters": [char.name for char in room.characters.values()],
                "transcript_length": len(room.transcript)
            }
    
    raise HTTPException(status_code=404, detail="Session not found")


@app.get("/sessions/{session_id}/transcript")
async def get_transcript(session_id: str, recent: Optional[int] = None):
    """Get session transcript"""
    for campaign_name, dm in session_manager.campaigns.items():
        if session_id in dm.active_sessions:
            room = dm.active_sessions[session_id]
            
            if recent:
                transcript = room.get_recent_events(recent)
            else:
                transcript = room.get_transcript()
            
            return {
                "session_id": session_id,
                "transcript": transcript
            }
    
    raise HTTPException(status_code=404, detail="Session not found")


@app.post("/sessions/dm_narrate")
async def dm_narrate(request: DMNarrateRequest):
    """DM narrates something"""
    for campaign_name, dm in session_manager.campaigns.items():
        if request.session_id in dm.active_sessions:
            room = dm.active_sessions[request.session_id]
            result = await room.dm_narrate(request.narration)
            
            # Broadcast
            await broadcast_to_session(request.session_id, {
                "type": "dm_narration",
                "text": request.narration
            })
            
            return result
    
    raise HTTPException(status_code=404, detail="Session not found")


@app.post("/sessions/character_action")
async def character_action(request: CharacterActionRequest):
    """Character performs an action"""
    for campaign_name, dm in session_manager.campaigns.items():
        if request.session_id in dm.active_sessions:
            room = dm.active_sessions[request.session_id]
            result = await room.character_action(
                request.character_id,
                request.action_description,
                request.action_type
            )
            
            # Broadcast
            await broadcast_to_session(request.session_id, {
                "type": "character_action",
                "character": result.get("character"),
                "action": result.get("action")
            })
            
            return result
    
    raise HTTPException(status_code=404, detail="Session not found")


# ============================================================================
# COMBAT ENDPOINTS
# ============================================================================

@app.post("/sessions/combat/start")
async def start_combat(request: StartCombatRequest):
    """Start combat encounter"""
    for campaign_name, dm in session_manager.campaigns.items():
        if request.session_id in dm.active_sessions:
            room = dm.active_sessions[request.session_id]
            result = await room.start_combat(request.enemies)
            
            # Broadcast
            await broadcast_to_session(request.session_id, {
                "type": "combat_started",
                "turn_order": result.get("turn_order")
            })
            
            return result
    
    raise HTTPException(status_code=404, detail="Session not found")


@app.post("/sessions/combat/action")
async def combat_action(request: CombatActionRequest):
    """Perform combat action"""
    for campaign_name, dm in session_manager.campaigns.items():
        if request.session_id in dm.active_sessions:
            room = dm.active_sessions[request.session_id]
            result = await room.combat_action(
                attacker_id=request.attacker_id,
                action_type=request.action_type,
                target_id=request.target_id,
                weapon=request.weapon,
                attack_bonus=request.attack_bonus,
                damage_dice=request.damage_dice,
                damage_bonus=request.damage_bonus
            )
            
            # Broadcast
            await broadcast_to_session(request.session_id, {
                "type": "combat_action",
                "message": result.get("message")
            })
            
            return result
    
    raise HTTPException(status_code=404, detail="Session not found")


@app.post("/sessions/{session_id}/combat/end")
async def end_combat(session_id: str):
    """End combat"""
    for campaign_name, dm in session_manager.campaigns.items():
        if session_id in dm.active_sessions:
            room = dm.active_sessions[session_id]
            result = await room.end_combat()
            
            # Broadcast
            await broadcast_to_session(session_id, {
                "type": "combat_ended",
                "message": result.get("message"),
                "winner": result.get("winner")
            })
            
            return result
    
    raise HTTPException(status_code=404, detail="Session not found")


@app.post("/sessions/{session_id}/end")
async def end_session(session_id: str):
    """End the session"""
    for campaign_name, dm in session_manager.campaigns.items():
        if session_id in dm.active_sessions:
            result = await dm.end_session(session_id)
            
            # Broadcast
            await broadcast_to_session(session_id, {
                "type": "session_ended",
                "result": result
            })
            
            return result
    
    raise HTTPException(status_code=404, detail="Session not found")


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/")
async def root():
    """Health check"""
    return {
        "service": "AI Society D&D",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "campaigns": len(session_manager.campaigns),
        "total_characters": len(session_manager.characters),
        "active_sessions": sum(
            len(dm.active_sessions) for dm in session_manager.campaigns.values()
        )
    }


# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
