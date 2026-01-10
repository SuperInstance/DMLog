"""
Demo Script - AI Society D&D System Test
=========================================
Demonstrates the complete system with:
1. Creating a campaign
2. Creating characters
3. Running a game session
4. Combat encounter
5. Memory formation and retrieval
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from enhanced_character import EnhancedCharacter, CharacterClass, DiceRoller
from game_room import DnDGameRoom, DungeonMaster, SessionManager
from game_mechanics import CombatEncounter
from memory_system import MemoryType


async def run_demo():
    """Run complete demo of the system"""
    
    print("=" * 70)
    print("AI SOCIETY D&D - TEMPORAL CONSCIOUSNESS DEMO")
    print("=" * 70)
    
    # ========================================================================
    # SETUP: Create Campaign and Characters
    # ========================================================================
    
    print("\n📚 Phase 1: Campaign Setup")
    print("-" * 70)
    
    # Create session manager
    manager = SessionManager()
    
    # Create campaign
    print("Creating campaign: 'Lost Mine of Phandelver'...")
    dm = manager.create_campaign(
        campaign_name="Lost_Mine_of_Phandelver",
        dm_id="human_dm",
        vector_db_url="http://localhost:6333"
    )
    
    # Add world lore
    print("Adding world lore...")
    dm.add_world_lore(
        "The town of Phandalin sits on the Sword Coast, a frontier settlement.",
        category="locations"
    )
    dm.add_world_lore(
        "Gundren Rockseeker has discovered the location of Wave Echo Cave.",
        category="plot"
    )
    dm.add_world_lore(
        "The Redbrands are a gang of thugs terrorizing Phandalin.",
        category="factions"
    )
    
    print(f"✓ Campaign created: {dm.campaign_name}")
    print(f"  World lore entries: {sum(len(v) for v in dm.world_lore.values())}")
    
    # Create characters
    print("\n👥 Creating characters...")
    
    # Character 1: Thorin Ironforge (Dwarf Fighter)
    thorin_class = CharacterClass(name="Fighter", level=3, features=["Second Wind", "Action Surge"])
    thorin = EnhancedCharacter(
        character_id="char_thorin",
        name="Thorin Ironforge",
        race="Dwarf",
        character_class=thorin_class,
        personality_traits=["Brave", "Stubborn", "Loyal to friends", "Distrusts elves"],
        backstory="A dwarf warrior whose clan's mine was destroyed by a dragon. Seeks revenge and glory.",
        use_local_vector_db=False  # Use fallback for demo
    )
    thorin.stats.strength = 16
    thorin.stats.constitution = 14
    thorin.stats.hit_points = 28
    thorin.stats.max_hit_points = 28
    thorin.stats.armor_class = 16
    thorin.inventory.weapon = "Battleaxe"
    thorin.inventory.armor = "Chain Mail"
    manager.register_character(thorin)
    
    # Character 2: Lyra Moonwhisper (Elf Wizard)
    lyra_class = CharacterClass(name="Wizard", level=3, spells_known=["Magic Missile", "Shield", "Fireball"])
    lyra = EnhancedCharacter(
        character_id="char_lyra",
        name="Lyra Moonwhisper",
        race="Elf",
        character_class=lyra_class,
        personality_traits=["Curious", "Cautious", "Values knowledge", "Dislikes violence"],
        backstory="An elven wizard searching for ancient magical artifacts to restore her family's library.",
        use_local_vector_db=False
    )
    lyra.stats.intelligence = 16
    lyra.stats.dexterity = 14
    lyra.stats.hit_points = 18
    lyra.stats.max_hit_points = 18
    lyra.stats.armor_class = 12
    lyra.inventory.weapon = "Quarterstaff"
    manager.register_character(lyra)
    
    print(f"✓ Created: {thorin.name} - Level {thorin.character_class.level} {thorin.race} {thorin.character_class.name}")
    print(f"  HP: {thorin.stats.hit_points}/{thorin.stats.max_hit_points}, AC: {thorin.stats.armor_class}")
    print(f"✓ Created: {lyra.name} - Level {lyra.character_class.level} {lyra.race} {lyra.character_class.name}")
    print(f"  HP: {lyra.stats.hit_points}/{lyra.stats.max_hit_points}, AC: {lyra.stats.armor_class}")
    
    # ========================================================================
    # GAME SESSION: Create and Start
    # ========================================================================
    
    print("\n🎮 Phase 2: Starting Game Session")
    print("-" * 70)
    
    # Create session
    room = dm.create_session(session_number=1)
    print(f"✓ Session created: {room.room_id}")
    
    # Add characters to session
    room.add_character(thorin)
    room.add_character(lyra)
    print(f"✓ Characters joined session")
    
    # Set scene
    room.game_state.current_location = "High Road to Phandalin"
    room.game_state.location_description = "A well-traveled dirt road through dense forest"
    
    # ========================================================================
    # GAMEPLAY: Narration and Actions
    # ========================================================================
    
    print("\n📖 Phase 3: Game Begins")
    print("-" * 70)
    
    # DM narrates opening
    await room.dm_narrate(
        "You're escorting a wagon along the High Road to Phandalin. "
        "The road winds through dense forest. Suddenly, you notice two dead horses "
        "blocking the path ahead, bristling with arrows."
    )
    print("DM: You're escorting a wagon... [full narration stored]")
    
    # Thorin investigates
    print("\n🛡️  Thorin's turn...")
    decision = await thorin.make_decision(
        situation="Dead horses blocking the road with arrows in them. Possible ambush ahead.",
        available_actions=[
            "Approach cautiously with weapon drawn",
            "Call out to see if anyone responds",
            "Search the area for tracks",
            "Turn the wagon around"
        ],
        use_memories=True
    )
    print(f"Thorin: {decision['action'][:150]}...")
    
    await room.character_action(
        character_id=thorin.character_id,
        action_description=decision['action']
    )
    
    # Store memory for Thorin
    thorin.store_game_memory(
        event_description="Encountered dead horses on the road, suspected goblin ambush",
        importance=6.0,
        emotional_valence=-0.3,
        participants=[lyra.character_id]
    )
    
    # Lyra casts detection spell
    print("\n🔮 Lyra's turn...")
    await room.character_action(
        character_id=lyra.character_id,
        action_description="I cast Detect Magic to see if there's any magical trap or illusion."
    )
    
    lyra.store_game_memory(
        event_description="Used Detect Magic to check for magical traps on the ambush site",
        importance=5.0,
        emotional_valence=-0.2,
        participants=[thorin.character_id]
    )
    
    # ========================================================================
    # COMBAT: Goblin Ambush
    # ========================================================================
    
    print("\n⚔️  Phase 4: Combat Encounter")
    print("-" * 70)
    
    # DM triggers ambush
    await room.dm_narrate(
        "Four goblins leap out from behind the trees, screeching and brandishing rusty scimitars!"
    )
    print("DM: Four goblins leap out from the trees!")
    
    # Start combat
    enemies = [
        {"name": "Goblin 1", "dex_mod": 2},
        {"name": "Goblin 2", "dex_mod": 2},
        {"name": "Goblin 3", "dex_mod": 1},
        {"name": "Goblin 4", "dex_mod": 2}
    ]
    
    combat_result = await room.start_combat(enemies)
    print(f"\n⚡ Combat begins! Initiative order:")
    for entry in combat_result['turn_order']:
        print(f"  - {entry['name']}: {entry['initiative']}")
    
    # Simulate a few combat rounds
    print("\n🎲 Round 1:")
    
    # Thorin attacks
    print("  Thorin attacks Goblin 1...")
    attack_result = await room.combat_action(
        attacker_id=thorin.character_id,
        action_type="attack",
        target_id="enemy_0",
        weapon="Battleaxe",
        attack_bonus=5,
        damage_dice="1d8",
        damage_bonus=3
    )
    print(f"    {attack_result['message']}")
    if attack_result['success']:
        print(f"    💥 Damage: {attack_result['damage']}")
    
    # End combat
    await room.end_combat()
    print("\n✓ Combat ended!")
    
    # Store combat memories
    thorin.store_game_memory(
        event_description="Fought and defeated goblin ambush on the High Road",
        importance=7.5,
        emotional_valence=0.6,
        participants=[lyra.character_id]
    )
    
    lyra.store_game_memory(
        event_description="Survived goblin ambush, Thorin fought bravely",
        importance=7.0,
        emotional_valence=0.3,
        participants=[thorin.character_id]
    )
    
    # ========================================================================
    # MEMORY SYSTEM: Show memories and consolidation
    # ========================================================================
    
    print("\n🧠 Phase 5: Memory System")
    print("-" * 70)
    
    print(f"\n{thorin.name}'s memories:")
    for mem_id, mem in list(thorin.memory_engine.memories.items())[-3:]:
        print(f"  • [{mem.memory_type.value}] {mem.content}")
        print(f"    Importance: {mem.importance}/10, Emotion: {mem.emotional_valence:+.1f}")
    
    print(f"\n{lyra.name}'s memories:")
    for mem_id, mem in list(lyra.memory_engine.memories.items())[-3:]:
        print(f"  • [{mem.memory_type.value}] {mem.content}")
        print(f"    Importance: {mem.importance}/10, Emotion: {mem.emotional_valence:+.1f}")
    
    # Show character journals
    print(f"\n📔 {thorin.name}'s Journal:")
    for entry in thorin.laptop.journal_entries[-2:]:
        print(f"  [{entry['timestamp'][:19]}] {entry['content'][:100]}...")
    
    # ========================================================================
    # SESSION END
    # ========================================================================
    
    print("\n🏁 Phase 6: End Session")
    print("-" * 70)
    
    result = await room.end_session()
    print(f"✓ Session ended")
    print(f"  Duration: {result['duration_minutes']} minutes")
    print(f"  Total events: {result['total_events']}")
    print(f"  Memories consolidated:")
    for char_name, count in result['memories_consolidated'].items():
        print(f"    - {char_name}: {count} memories")
    
    # Archive to DM's master DB
    await dm.end_session(room.room_id)
    print(f"✓ Session archived to campaign master database")
    
    # ========================================================================
    # DEMONSTRATE MEMORY RETRIEVAL
    # ========================================================================
    
    print("\n🔍 Phase 7: Memory-Driven Decisions")
    print("-" * 70)
    
    # Query DM's master database
    print("\nDM queries campaign history:")
    history = dm.query_campaign_history("What happened with the goblins?")
    print(f"  Found {history['total_results']} relevant memories")
    if history['relevant_events']:
        print(f"  Recent event: {history['relevant_events'][0][:100]}...")
    
    # Show that next time Thorin encounters goblins, he'll remember
    print(f"\n{thorin.name} encounters goblins again (hypothetical):")
    print("  His vector DB will retrieve:")
    print("    - 'Fought and defeated goblin ambush on the High Road'")
    print("    - Importance: 7.5/10, Positive emotion")
    print("  Decision influence: More confident, less cautious")
    
    # ========================================================================
    # STATS & SUMMARY
    # ========================================================================
    
    print("\n📊 Final Statistics")
    print("-" * 70)
    
    campaign_stats = dm.get_campaign_stats()
    print(f"Campaign: {campaign_stats['campaign_name']}")
    print(f"  Total sessions: {campaign_stats['total_sessions']}")
    print(f"  World lore entries: {campaign_stats['world_lore_entries']}")
    
    print(f"\n{thorin.name}:")
    print(f"  Total memories: {len(thorin.memory_engine.memories)}")
    print(f"  Journal entries: {len(thorin.laptop.journal_entries)}")
    print(f"  Identity coherence: {thorin.identity_system.get_identity_coherence_index([], 30):.2f}")
    
    print(f"\n{lyra.name}:")
    print(f"  Total memories: {len(lyra.memory_engine.memories)}")
    print(f"  Journal entries: {len(lyra.laptop.journal_entries)}")
    print(f"  Identity coherence: {lyra.identity_system.get_identity_coherence_index([], 30):.2f}")
    
    # ========================================================================
    # DONE
    # ========================================================================
    
    print("\n" + "=" * 70)
    print("✅ DEMO COMPLETE!")
    print("=" * 70)
    print("\nKey Features Demonstrated:")
    print("  ✓ Campaign & character creation")
    print("  ✓ Game session with narration")
    print("  ✓ Memory-driven character decisions")
    print("  ✓ D&D combat mechanics")
    print("  ✓ Memory formation and storage")
    print("  ✓ Character journals (laptops)")
    print("  ✓ Session transcripts")
    print("  ✓ DM master database")
    print("  ✓ Memory consolidation")
    print("\nNext Steps:")
    print("  • Start API server: python backend/api_server.py")
    print("  • Try the REST API with curl (see README)")
    print("  • Build a web UI for easier interaction")
    print("  • Add more characters and run multi-session campaigns!")


if __name__ == "__main__":
    asyncio.run(run_demo())
