"""
Clash of Clans Troop & Spell Housing Space (Capacity) Database.
Contains verified housing spaces for all standard, dark, super, and seasonal troops and spells.
"""

from typing import Dict, List, Tuple

# Housing space required per individual troop unit in Army Camps
TROOP_HOUSING_SPACE: Dict[str, int] = {
    # 1. Regular Elixir Troops
    "Barbarian": 1,
    "Archer": 1,
    "Giant": 5,
    "Goblin": 1,
    "Wall Breaker": 2,
    "Balloon": 5,
    "Wizard": 4,
    "Healer": 14,
    "Dragon": 20,
    "P.E.K.K.A": 25,
    "Baby Dragon": 10,
    "Miner": 6,
    "Electro Dragon": 30,
    "Yeti": 18,
    "Dragon Rider": 25,
    "Electro Titan": 32,
    "Root Rider": 20,
    "Thrower": 16,

    # 2. Dark Elixir Troops
    "Minion": 2,
    "Hog Rider": 5,
    "Valkyrie": 8,
    "Golem": 30,
    "Witch": 12,
    "Lava Hound": 30,
    "Bowler": 6,
    "Ice Golem": 15,
    "Headhunter": 6,
    "Apprentice Warden": 20,
    "Druid": 16,
    "Furnace": 18,
    "Momma": 25,
    "Ruin Witch": 26,
    "Meteor Golem": 40,

    # 3. Super Troops
    "Super Barbarian": 5,
    "Super Archer": 12,
    "Super Giant": 10,
    "Sneaky Goblin": 3,
    "Super Wall Breaker": 8,
    "Rocket Balloon": 8,
    "Super Wizard": 10,
    "Super Dragon": 40,
    "Inferno Dragon": 15,
    "Super Minion": 12,
    "Super Valkyrie": 20,
    "Super Witch": 40,
    "Ice Hound": 40,
    "Super Bowler": 30,
    "Super Miner": 24,
    "Super Hog Rider": 12,
    "Super Yeti": 30,
}

# Housing space required per individual spell in Spell Storage
SPELL_HOUSING_SPACE: Dict[str, int] = {
    "Lightning": 1,
    "Healing": 2,
    "Rage": 2,
    "Jump": 2,
    "Freeze": 1,
    "Clone": 3,
    "Invisibility": 1,
    "Recall": 2,
    "Revive Spell": 2,
    "Overgrowth": 2,
    "Poison": 1,
    "Earthquake": 1,
    "Haste": 1,
    "Skeleton": 1,
    "Bat": 1,
    "Ice Block": 1,
    "Totem Spell": 1,
}


def get_troop_space(troop_name: str) -> int:
    """Returns housing space for a given troop name (case-insensitive and format-tolerant)."""
    clean_name = troop_name.replace("_", " ").strip().title()
    if clean_name in TROOP_HOUSING_SPACE:
        return TROOP_HOUSING_SPACE[clean_name]
    for k, v in TROOP_HOUSING_SPACE.items():
        if k.lower().replace(" ", "") == clean_name.lower().replace(" ", ""):
            return v
    return 1  # Default fallback


def get_spell_space(spell_name: str) -> int:
    """Returns housing space for a given spell name (case-insensitive and format-tolerant)."""
    clean_name = spell_name.replace("_", " ").strip().title().replace(" Spell", "")
    if clean_name in SPELL_HOUSING_SPACE:
        return SPELL_HOUSING_SPACE[clean_name]
    for k, v in SPELL_HOUSING_SPACE.items():
        if k.lower().replace(" ", "") == clean_name.lower().replace(" ", ""):
            return v
    return 1  # Default fallback


def calculate_army_housing_space(troops_data: List[Tuple[str, int, bool]]) -> Tuple[int, List[dict]]:
    """
    Calculates total used army camp housing space and per-troop breakdown.
    Each item in troops_data is: (unit_name, quantity, is_enabled).
    Returns (total_space, breakdown_list).
    """
    total_space = 0
    breakdown = []
    for name, qty, enabled in troops_data:
        if not enabled or qty <= 0:
            continue
        unit_space = get_troop_space(name)
        slot_total = unit_space * qty
        total_space += slot_total
        breakdown.append({
            "name": name,
            "unit_space": unit_space,
            "quantity": qty,
            "total_space": slot_total
        })
    return total_space, breakdown


def calculate_spell_housing_space(spells_data: List[Tuple[str, int, bool]]) -> Tuple[int, List[dict]]:
    """
    Calculates total used spell storage housing space and per-spell breakdown.
    Each item in spells_data is: (spell_name, quantity, is_enabled).
    Returns (total_space, breakdown_list).
    """
    total_space = 0
    breakdown = []
    for name, qty, enabled in spells_data:
        if not enabled or qty <= 0:
            continue
        unit_space = get_spell_space(name)
        slot_total = unit_space * qty
        total_space += slot_total
        breakdown.append({
            "name": name,
            "unit_space": unit_space,
            "quantity": qty,
            "total_space": slot_total
        })
    return total_space, breakdown
