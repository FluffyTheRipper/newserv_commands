import asyncio
import json
import requests
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Input, RichLog

# --- CONFIGURATION ---
SERVER_IP = "192.168.1.99"
PORT = "8999"
HTTP_SECRET = ""  # Leave as "" if not used

# The API root path matches your documentation prefix '/y'
BASE_URL = f"http://{SERVER_IP}:{PORT}/y"
# ---------------------

class NewservDashboard(App):
    CSS = """
    Screen {
        background: #1a1b26;
    }
    #main-layout {
        layout: horizontal;
        height: 1fr;
    }
    #left-pane {
        width: 30%;
        height: 100%;
        border-right: solid #3b4261;
        padding: 1;
    }
    #right-pane {
        width: 70%;
        height: 100%;
    }
    .metric-box {
        background: #24283c;
        border: round #7aa2f7;
        margin-bottom: 1;
        padding: 1;
        height: auto;
    }
    #log-pane {
        height: 1fr;
        border: tall #3b4261;
        background: #16161e;
    }
    Input {
        dock: bottom;
        border: tall #7aa2f7;
        background: #24283c;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit Dashboard"),
        ("r", "refresh", "Manual Refresh")
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Container(id="main-layout"):
            # Left Sidebar: Realtime Metrics & Stats
            with Vertical(id="left-pane"):
                yield Static("Loading server specs...", id="stat-server", classes="metric-box")
                yield Static("Loading active players...", id="stat-players", classes="metric-box")
                yield Static("Loading active lobbies...", id="stat-lobbies", classes="metric-box")
            
            # Right Main Window: Command execution history log & input bar
            with Vertical(id="right-pane"):
                yield RichLog(id="log-pane", highlight=True, markup=True)
                yield Input(placeholder="Enter server shell command here (e.g., status, help)...", id="cmd-input")
                
        yield Footer()

    def on_mount(self) -> None:
        """Kicks off background refresh loops when the app boots up."""
        self.log_widget = self.query_one("#log-pane", RichLog)
        self.log_widget.write("[bold green]Dashboard Initialized.[/bold green] Connected to " + BASE_URL)
        self.log_widget.write("Type commands in the box below. Press [bold]Q[/bold] to exit safely.\n" + ("-" * 60))
        
        # Start background loop to auto-refresh metrics every 5 seconds
        self.set_interval(5.0, self.update_metrics)
        self.update_metrics()

    def get_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if HTTP_SECRET:
            headers["X-Newserv-Secret"] = HTTP_SECRET
        return headers

    def update_metrics(self) -> None:
        """Polls the API summary endpoint to fetch data state safely."""
        try:
            # We target the summary endpoint to gather comprehensive context efficiently
            response = requests.get(f"{BASE_URL}/summary", headers=self.get_headers(), timeout=2)
            if response.status_code == 200:
                data = response.json()
                
                # Update Server Base Info
                self.query_one("#stat-server", Static).update(
                    "[bold cyan]🖥️ SERVER METRICS[/bold cyan]\n"
                    f"Version: {data.get('server_version', 'newserv')}\n"
                    f"State: Online"
                )
                
                # Update Client Connections
                clients = data.get("clients", [])
                client_count = len(clients)
                player_list = "\n".join([f" • {c.get('name', 'Unknown')} ({c.get('version', '??')})" for c in clients]) if client_count > 0 else " • None"
                self.query_one("#stat-players", Static).update(
                    f"[bold green]👥 PLAYERS ONLINE ({client_count})[/bold green]\n{player_list}"
                )
                
                # Update Lobbies / Active Games
                lobbies = data.get("lobbies", [])
                lobby_count = len(lobbies)
                self.query_one("#stat-lobbies", Static).update(
                    f"[bold magenta]🎮 ACTIVE LOBBIES ({lobby_count})[/bold magenta]\n" +
                    "\n".join([f" • {l.get('name', 'Lobby')} ({len(l.get('client_ids', []))}/12)" for l in lobbies[:5]])
                )
        except Exception as e:
            self.query_one("#stat-server", Static).update("[bold red]❌ Connection Error[/bold red]")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Intercepts the Enter key inside the text box, executes, and updates terminal log."""
        command_text = event.value.strip()
        if not command_text:
            return

        # Clear text bar immediately for snappier UI feel
        input_widget = self.query_one("#cmd-input", Input)
        input_widget.value = ""

        # Print command echoing into console
        self.log_widget.write(f"\n[bold yellow]newserv>[/bold yellow] {command_text}")

        # Offload the blocking HTTP POST request to a background execution worker thread
        asyncio.create_task(self.run_shell_command(command_text))

    async def run_shell_command(self, command_text: str) -> None:
        """Runs the API command call asynchronously without freezing the app window."""
        loop = asyncio.get_event_loop()
        try:
            payload = json.dumps({"command": command_text})
            
            # Execute synchronous request inside async thread runner
            response = await loop.run_in_executor(
                None, 
                lambda: requests.post(f"{BASE_URL}/shell-exec", headers=self.get_headers(), data=payload, timeout=5)
            )
            
            if response.status_code == 200:
                result_data = response.json()
                raw_output = result_data.get("result", "").strip()
                if raw_output:
                    self.log_widget.write(raw_output)
                else:
                    self.log_widget.write("[dim italic](Command completed with no output returns)[/dim italic]")
            else:
                self.log_widget.write(f"[bold red]Server returned HTTP Error Status: {response.status_code}[/bold red]")
        except Exception as e:
            self.log_widget.write(f"[bold red]Failed to dispatch command execution payload: {e}[/bold red]")

    def action_refresh(self) -> None:
        """Allows tapping 'R' key to instantly bypass the 5-second interval timer."""
        self.update_metrics()
        self.log_widget.write("[dim italic]Metrics refreshed manually.[/dim italic]")

if __name__ == "__main__":
    app = NewservDashboard()
    app.run()