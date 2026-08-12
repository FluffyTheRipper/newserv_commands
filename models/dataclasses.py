# immutable schemas for Player, Game, ServerMetrics

from dataclasses import dataclass, field
from typing import List, Dict, Optional



@dataclass(frozen=True)
class Player:
    account_id: str # Unique identifier for the player's account
    char_name: str 
    char_level: int
    char_class: str
    is_online: bool
    rare_drops: List[str] # not sure how to implement this yet

    @property
    def display_string(self) -> str: # placeholder, str representation of the player for terminal display
        status_emoji = "🟢" if self.is_online else "🔴"
        return f"{status_emoji} {self.char_name} (Lvl {self.char_level} {self.char_class})"

@dataclass(frozen=True)
class GameLobby:
    id: str
    name: str
    difficulty: str
    episode: str
    client_ids: List[Player] = field(default_factory=list)  # List of account_ids of players in this lobby

@dataclass(frozen=True)
class ServerMetrics:
    start_time: Optional[str]  # ISO timestamp of when the server started, calculate uptime from this later
    uptime_usecs: int
    game_count: int
    client_count: int

    @property
    def formatted_uptime(self) -> str:
        """Converts microseconds into a human-readable days/hours/minutes format."""
        if not self.uptime_usecs:
            return "Offline"
        
        uptime_seconds = self.uptime_usecs // 1_000_000
        days = uptime_seconds // 86400
        hours = (uptime_seconds % 86400) // 3600
        minutes = (uptime_seconds % 3600) // 60
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        return f"{hours}h {minutes}m"

@dataclass(frozen=True)
class ServerState:
    """Snapshot of the server's current state."""
    metrics: ServerMetrics
    players: Dict[int, Player] = field(default_factory=dict)
    lobbies: Dict[int, GameLobby] = field(default_factory=dict)