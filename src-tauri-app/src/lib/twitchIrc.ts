/**
 * Twitch IRC WebSocket client.
 *
 * Connects to Twitch chat, parses commands, dispatches handlers.
 * Runs entirely in the frontend — no Python or Rust needed.
 */
import { createSignal } from "solid-js";

const TWITCH_IRC_URL = "wss://irc-ws.chat.twitch.tv:443";

export type ConnectionStatus = "disconnected" | "connecting" | "connected" | "error";

// --- Reactive state ---
const [connectionStatus, setConnectionStatus] = createSignal<ConnectionStatus>("disconnected");
const [connectedChannel, setConnectedChannel] = createSignal<string>("");

export { connectionStatus, connectedChannel };

// --- Internal state ---
let ws: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let reconnectAttempt = 0;
let currentToken = "";
let currentUsername = "";
let currentChannel = "";
let commandHandler: ((user: string, command: string, args: string) => void) | null = null;

// Rate limiting: track last command time per user
const userCooldowns = new Map<string, number>();
let lastGlobalCommand = 0;
const USER_COOLDOWN_MS = 5000;
const GLOBAL_COOLDOWN_MS = 1000;

export function setCommandHandler(
  handler: (user: string, command: string, args: string) => void,
): void {
  commandHandler = handler;
}

export function connect(token: string, username: string, channel: string): void {
  if (ws && ws.readyState === WebSocket.OPEN) {
    disconnect();
  }

  currentToken = token;
  currentUsername = username.toLowerCase();
  currentChannel = channel.toLowerCase().replace(/^#/, "");

  setConnectionStatus("connecting");
  reconnectAttempt = 0;

  _doConnect();
}

export function disconnect(): void {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  if (ws) {
    ws.onclose = null; // prevent reconnect
    ws.close();
    ws = null;
  }
  setConnectionStatus("disconnected");
  setConnectedChannel("");
}

export function sendMessage(text: string): void {
  if (ws && ws.readyState === WebSocket.OPEN && currentChannel) {
    ws.send(`PRIVMSG #${currentChannel} :${text}`);
  }
}

function _doConnect(): void {
  ws = new WebSocket(TWITCH_IRC_URL);

  ws.onopen = () => {
    if (!ws) return;
    // Request tags for display name, badges, etc.
    ws.send("CAP REQ :twitch.tv/tags twitch.tv/commands");
    ws.send(`PASS oauth:${currentToken}`);
    ws.send(`NICK ${currentUsername}`);
    ws.send(`JOIN #${currentChannel}`);
  };

  ws.onmessage = (event) => {
    const raw = event.data as string;
    for (const line of raw.split("\r\n")) {
      if (!line) continue;
      _handleLine(line);
    }
  };

  ws.onclose = () => {
    setConnectionStatus("disconnected");
    setConnectedChannel("");
    _scheduleReconnect();
  };

  ws.onerror = () => {
    setConnectionStatus("error");
  };
}

function _scheduleReconnect(): void {
  if (!currentToken || !currentChannel) return;
  const delay = Math.min(30000, 1000 * Math.pow(2, reconnectAttempt));
  reconnectAttempt++;
  reconnectTimer = setTimeout(() => {
    setConnectionStatus("connecting");
    _doConnect();
  }, delay);
}

function _handleLine(line: string): void {
  // Handle PING
  if (line.startsWith("PING")) {
    ws?.send("PONG :tmi.twitch.tv");
    return;
  }

  // Successful login
  if (line.includes("001") || line.includes(":Welcome")) {
    setConnectionStatus("connected");
    setConnectedChannel(currentChannel);
    reconnectAttempt = 0;
    return;
  }

  // Login failure
  if (line.includes("Login authentication failed")) {
    setConnectionStatus("error");
    disconnect();
    return;
  }

  // Parse PRIVMSG
  const privmsgMatch = line.match(
    /^(?:@\S+ )?:(\w+)!\w+@\w+\.tmi\.twitch\.tv PRIVMSG #\w+ :(.+)$/,
  );
  if (!privmsgMatch) return;

  const [, username, message] = privmsgMatch;
  const trimmed = message.trim();

  // Only process commands starting with !
  if (!trimmed.startsWith("!")) return;

  // Rate limiting
  const now = Date.now();
  if (now - lastGlobalCommand < GLOBAL_COOLDOWN_MS) return;

  const userKey = username.toLowerCase();
  const lastUserCmd = userCooldowns.get(userKey) || 0;
  if (now - lastUserCmd < USER_COOLDOWN_MS) return;

  lastGlobalCommand = now;
  userCooldowns.set(userKey, now);

  // Clean up old cooldown entries periodically
  if (userCooldowns.size > 1000) {
    const cutoff = now - USER_COOLDOWN_MS * 2;
    for (const [k, v] of userCooldowns) {
      if (v < cutoff) userCooldowns.delete(k);
    }
  }

  // Parse command and args
  const spaceIdx = trimmed.indexOf(" ");
  const command = spaceIdx > 0 ? trimmed.substring(1, spaceIdx).toLowerCase() : trimmed.substring(1).toLowerCase();
  const args = spaceIdx > 0 ? trimmed.substring(spaceIdx + 1).trim() : "";

  commandHandler?.(username, command, args);
}
