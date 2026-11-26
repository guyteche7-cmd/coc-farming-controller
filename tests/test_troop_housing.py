"""
Unit tests for Troop Housing Space database and capacity calculators.
"""

from src.planning.troop_housing import (
    TROOP_HOUSING_SPACE,
    SPELL_HOUSING_SPACE,
    get_troop_space,
    get_spell_space,
    calculate_army_housing_space,
    calculate_spell_housing_space,
)


def test_troop_housing_space_constants():
    assert TROOP_HOUSING_SPACE["Barbarian"] == 1
    assert TROOP_HOUSING_SPACE["Archer"] == 1
    assert TROOP_HOUSING_SPACE["Giant"] == 5
    assert TROOP_HOUSING_SPACE["Valkyrie"] == 8
    assert TROOP_HOUSING_SPACE["Super Wall Breaker"] == 8
    assert TROOP_HOUSING_SPACE["Super Dragon"] == 40
    assert TROOP_HOUSING_SPACE["Dragon"] == 20
    assert TROOP_HOUSING_SPACE["P.E.K.K.A"] == 25
    assert TROOP_HOUSING_SPACE["Electro Titan"] == 32
    assert TROOP_HOUSING_SPACE["Root Rider"] == 20


def test_spell_housing_space_constants():
    assert SPELL_HOUSING_SPACE["Lightning"] == 1
    assert SPELL_HOUSING_SPACE["Healing"] == 2
    assert SPELL_HOUSING_SPACE["Rage"] == 2
    assert SPELL_HOUSING_SPACE["Jump"] == 2
    assert SPELL_HOUSING_SPACE["Freeze"] == 1
    assert SPELL_HOUSING_SPACE["Clone"] == 3
    assert SPELL_HOUSING_SPACE["Invisibility"] == 1
    assert SPELL_HOUSING_SPACE["Earthquake"] == 1
    assert SPELL_HOUSING_SPACE["Totem Spell"] == 1


def test_get_troop_space_tolerance():
    assert get_troop_space("valkyrie") == 8
    assert get_troop_space("super_wall_breaker") == 8
    assert get_troop_space("Super Wall Breaker") == 8
    assert get_troop_space("dragon") == 20
    assert get_troop_space("non_existent_troop") == 1


def test_get_spell_space_tolerance():
    assert get_spell_space("earthquake") == 1
    assert get_spell_space("Totem Spell") == 1
    assert get_spell_space("totem_spell") == 1
    assert get_spell_space("healing") == 2
    assert get_spell_space("rage") == 2


def test_calculate_army_housing_space():
    # 44 Valkyries * 8 space = 352 (Max TH17 army camp)
    troops_data = [
        ("Valkyrie", 44, True),
    ]
    total, breakdown = calculate_army_housing_space(troops_data)
    assert total == 352
    assert len(breakdown) == 1
    assert breakdown[0]["unit_space"] == 8
    assert breakdown[0]["total_space"] == 352


def test_calculate_army_housing_space_mixed():
    troops_data = [
        ("Valkyrie", 24, True),          # 24 * 8 = 192
        ("Super Wall Breaker", 4, True), # 4 * 8 = 32
        ("Dragon", 5, True),             # 5 * 20 = 100
        ("Healer", 2, False),            # Disabled -> 0
    ]
    total, breakdown = calculate_army_housing_space(troops_data)
    assert total == 192 + 32 + 100
    assert len(breakdown) == 3


def test_calculate_spell_housing_space():
    spells_data = [
        ("Totem Spell", 11, True),  # 11 * 1 = 11
        ("Rage", 1, False),        # Disabled -> 0
    ]
    total, breakdown = calculate_spell_housing_space(spells_data)
    assert total == 11
    assert len(breakdown) == 1
