import re

DIFFICULTY_SHORTHAND = {
    "Normal": "Norm",
    "Hard": "Hard",
    "Very Hard": "V. Hard",
    "Ultimate": "Ult"
}

EPISODE_SHORTHAND = {
    "Episode 1": "EP1",
    "Episode 2": "EP2",
    "Episode 4": "EP4"
}

def clean_item_name(raw_item_name: str) -> str:
    """
    Strips leading color code sequences and trims off trailing
    weapon percentages or armor/shield grind suffixes.
    """
    # 1. Remove leading color indicators/question marks common in server memory streams
    clean_step = raw_item_name.replace("???? ", "").replace("????", "")
    
    # 2. Slice off trailing stats (e.g., " [0/25/0/0|10]" or " +10")
    # This matches spaces followed by numbers/slashes or a plus sign
    item_name = re.sub(r'\s+([-+]?\d+[\d/]*|\d+/\d+/\d+/\d+).*$', '', clean_step)
    return item_name.strip()


def format_game_title(name: str, episode: str, difficulty: str) -> str:
    """Formats game room titles into consistent Discord-friendly strings."""
    diff_short = DIFFICULTY_SHORTHAND.get(difficulty, difficulty)
    ep_short = EPISODE_SHORTHAND.get(episode, episode)
    return f"'{name}' - *{ep_short} {diff_short}*"