# Loose todo / potential feature list


Server event logging 
    - state machine (server status, player count, uptime)
    - player events (logins, logouts, rare drops)
     - monitor the REST API for changes in these states/events
       - send updates to Discord via webhooks

Log player statistics?
    - track player logins/logouts and send updates to Discord
    - track rare drops and send updates to Discord
    - track server uptime and send periodic updates to Discord
    - track number of rare drops on the server? (log each, summarize by item maybe?)
    - 

Separate the status and rare drop webhooks for better organization and potential future expansion (e.g., adding more event types or channels).

OOP?
    - dataclass that holds the server state (/summary endpoint data)
    - verify previous state vs new state to determine what events to send to Discord
    - separate functions for handling different event types (status updates, player events, rare drops)