import json
import time
import threading
import requests
import re
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import websocket
import asyncio
import websockets
from discord_webhook import DiscordWebhook, DiscordEmbed
from dotenv import load_dotenv
import os

http_session = requests.Session()  # Reuse HTTP session for efficiency
retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
http_session.mount("http://", HTTPAdapter(max_retries=retries))


# --- CONFIGURATION ---
load_dotenv()  # Load environment variables from .env file if present
STATUS_WEBHOOK_URL = os.getenv("STATUS_WEBHOOK_URL")
RARE_DROPS_WEBHOOK_URL = os.getenv("RARE_DROPS_WEBHOOK_URL")
GAME_SERVER_API = os.getenv("GAME_SERVER_API")

# GET endpoints
CLIENTS_ENDPOINT = f"{GAME_SERVER_API}/clients"
SERVER_ENDPOINT = f"{GAME_SERVER_API}/server"
SUMMARY_ENDPOINT = f"{GAME_SERVER_API}/summary"

# Websocket endpoints
# RARE_DROPS_STREAM_ENDPOINT = f"{GAME_SERVER_API}/rare-drops/stream"
RARE_DROPS_STREAM_ENDPOINT = "ws://192.168.1.99:8999/y/rare-drops/stream"  # This will be converted to ws:// in the code
WS_DROPS_STREAM_ENDPOINT = RARE_DROPS_STREAM_ENDPOINT.replace("http://", "ws://").replace("https://", "wss://")

POLL_INTERVAL_SEC = 30  # Check server status every 30 seconds

DIFFICULTY_EMOJIS = {
    "Normal": "🟢",
    "Hard": "🔵",
    "Very Hard": "🟣",
    "Ultimate": "🔴"
}

DIFFICULTY_SHORTHAND = {
    "Normal": "Norm",
    "Hard": "Hard",
    "Very Hard": "V. Hard",
    "Ultimate": "Ult"
}

EPISODE_SHORTHAND = {
    "Episode 1": "EP1",
    "Episode 2": "EP2"
}


def send_to_discord(title, description, color="00ff00", fields=None, thumbnail=False, target_webhook=None):
    """Utility to send clean, embedded messages to Discord with automatic rate-limit retries."""
    RARE_BOX_URL = ""
    webhook = DiscordWebhook(url=target_webhook, rate_limit_retry=True)
    
    embed = DiscordEmbed(title=title, description=description, color=color)
    embed.set_timestamp()
    
    if fields:
        for name, value in fields.items():
            embed.add_embed_field(name=name, value=str(value), inline=False)

    if thumbnail:
        embed.set_thumbnail(url=RARE_BOX_URL)

    webhook.add_embed(embed)
    try:
        webhook.execute()
    except Exception as e:
        print(f"Failed to send to Discord: {e}")

# --- TASK 1: POLLING STATUS ENDPOINT ---
def poll_server_status():
    """Periodically fetches server status and alerts if something changes."""
    print("Started Status Polling Thread...")
    last_state = None
    last_client_count = None
    last_game_count = None

    while True:
        try:
            response = http_session.get(SUMMARY_ENDPOINT, timeout=10)
            
            if response.status_code == 200:
                data = response.json() # e.g., {"status": "online", "players": 14, "max_players": 50}
                server_data = data.get("Server", {})

                # server status
                server_uptime_us = server_data.get("UptimeUsecs", 0)
                game_count = server_data.get("GameCount", 0)
                client_count = server_data.get("ClientCount", 0)
                
                # convert us to readable format
                uptime_seconds = server_uptime_us // 1_000_000 if server_uptime_us else 0
                days = uptime_seconds // 86400
                hours = (uptime_seconds % 86400) // 3600
                minutes = (uptime_seconds % 3600) // 60
                # Format dynamically: include days only if the server has been up for more than 24 hours
                if uptime_seconds:
                    server_uptime = (
                        f"{days}d {hours}h {minutes}m" if days > 0 else f"{hours}h {minutes}m"
                    )
                else:
                    server_uptime = "Offline"

                if client_count == last_client_count and game_count == last_game_count and last_state == "online":
                    time.sleep(POLL_INTERVAL_SEC)
                    continue  # No change in status, skip sending an update

                # games
                # create dict of gameID to gameName for lookups with player data
                games_map = {}
                for game in data.get("Games", []):
                    g_id = game.get("ID")
                    if g_id:
                        games_map[g_id] = {
                            "Name": game.get("Name"),
                            "Episode": game.get("Episode"),
                            "Difficulty": game.get("Difficulty"),
                            "players": []
                        }

                # lobby players (not in a game), in LobbyID 1-15
                lobby_players = []
                for client in data.get("Clients", []):
                    c_lobby_id = client.get("LobbyID")
                    c_name = client.get("Name")
                    if not c_name:
                        continue # Skip clients without a name (e.g., bots or placeholders)
                    player_string = f"-   **{client.get('Name')}** (Lv.{client.get('Level')} {client.get('Class')})"

                    if c_lobby_id in games_map: # in a game lobby
                        games_map[c_lobby_id]["players"].append(player_string)
                    else: # otherwise, in a lobby 
                        lobby_players.append(player_string)

                # Build the embed fields dynamically based on lobby and game data
                embed_fields = {}

                if lobby_players: # is lobby players
                    field_title = f"Lobby"
                    field_value = "\n".join(lobby_players)
                    embed_fields[field_title] = field_value
                
                if games_map: # is active games
                    for game_id, game_info in games_map.items():
                        diff_short = DIFFICULTY_SHORTHAND.get(game_info['Difficulty'], game_info['Difficulty'])
                        ep_short = EPISODE_SHORTHAND.get(game_info['Episode'], game_info['Episode'])
                        field_title = f"\'{game_info['Name']}\' - *{ep_short} {diff_short}*"
                        if game_info['players']:
                            field_value = "\n".join(game_info['players'])
                        else:
                            field_value = "*• 0 players ($persist lobby)*"
                        embed_fields[field_title] = field_value

                if client_count == 0:
                    description_str = "Nobody grinding atm. Server schleep... 💤"
                else:
                    description_str = ""

                send_to_discord(
                    title=f"📊 Server Uptime: {server_uptime}",
                    description=f"{description_str}",
                    color="03b2f8",
                    fields=embed_fields,
                    target_webhook=STATUS_WEBHOOK_URL
                    )
                
                last_client_count = client_count
                last_game_count = game_count
                last_state = "online"
            else:
                print(f"Status API returned code {response.status_code}")

        except requests.exceptions.Timeout:
            # Silently log timeouts to the terminal instead of spamming Discord
            print("⚠️ Status API request timed out because the server was busy. Retrying next cycle...")

        except requests.exceptions.RequestException as e:
            if last_state != "offline":
                print(f"Error connecting to server: {e}")
                send_to_discord("🚨 Server Unreachable", "Unable to connect to the game server REST API.", "ff0000")
                last_state = "offline"
                
        time.sleep(POLL_INTERVAL_SEC)

# --- TASK 2: STREAMING LIVE ITEM DROPS ---
def start_stream_thread():
    """Wrapper to run our modern async websocket listener inside your existing threading architecture."""
    def run_async_loop():
        asyncio.run(async_stream_listener())
        
    threading.Thread(target=run_async_loop, daemon=True).start()

async def async_stream_listener():
    # Convert your http path to standard ws path
    ws_url = WS_DROPS_STREAM_ENDPOINT.replace("http://", "ws://").replace("https://", "wss://")    
    while True:
        try:
            async with websockets.connect(ws_url, ping_interval=10, ping_timeout=5) as websocket:
                print("⚡ Native WebSockets Connection Established!")
                
                # Continuously wait for raw text fragments from newserv
                async for message in websocket:
                    try:
                        # Force ensure the incoming message is a clean string format
                        if isinstance(message, bytes):
                            message_str = message.decode('utf-8', errors='ignore')
                        else:
                            message_str = str(message)

                        # Trim any weird leading/trailing whitespace buffers from the wire
                        message_str = message_str.strip()

                        # Parse the native server JSON safely
                        drop_data = json.loads(message_str)
                        
                        # Skip the handshake server-info packet 
                        if "ServerType" in drop_data:
                            continue
                            
                        # Extract and clean values
                        player = drop_data.get("PlayerName", "Unknown Hunter")
                        game_name = drop_data.get("GameName", "Lobby")
                        raw_item_name = drop_data.get("ItemDescription", "Unknown Item")
                        
                        # 1. Strip out the leading color codes (????)
                        clean_step = raw_item_name.replace("???? ", "").replace("????", "")
                        # 2. Chop off trailing percentages (e.g., 0/25/0/0) or grinds (e.g., +10)
                        # This matches anything starting with spaces followed by numbers/slashes or a plus sign
                        item_name = re.sub(r'\s+([-+]?\d+[\d/]*|\d+/\d+/\d+/\d+).*$', '', clean_step).strip()

                        send_to_discord(
                            title="✨ RARE ITEM FOUND ✨",
                            description=f"**{player}** found **{item_name}**!",
                            color="ff0000",
                            thumbnail=True,
                            target_webhook=RARE_DROPS_WEBHOOK_URL
                        )
                        
                    except json.JSONDecodeError as jde:
                        # This will print the problematic payload layout so we can pinpoint exactly what it didn't like
                        print(f"⚠️ JSON parsing hiccup: {jde} | Raw content: {repr(message)}")
                        continue
                    except Exception as loop_err:
                        print(f"Error executing webhook delivery: {loop_err}")
                        
        except Exception as conn_error:
            print(f"Pipeline disconnected ({conn_error}). Retrying connection in 5s...")
            await asyncio.sleep(5)


# --- MAIN EXECUTION ---
if __name__ == "__main__":
    # Start your existing polling function 
    status_thread = threading.Thread(target=poll_server_status, daemon=True)
    status_thread.start()
    
    # Start the new async websocket pipeline wrapper
    start_stream_thread()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down bridge script...")