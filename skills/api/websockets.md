---
id: websockets
name: WebSockets
category: api
level1: "For real-time communication, WebSocket connections, Socket.io, and live updates"
platforms: [claude-code, cursor, codex, gemini-cli, antigravity, opencode, aider, windsurf]
priority: 2
keywords: [websocket, socket.io, real-time, ws, live-update, push-notification, event-driven]
level1_tokens: 45
level2_tokens: 480
level3_tokens: 2100
author: agentkit-team
version: 1.0.0
---

<!-- LEVEL 1 START -->
## WebSockets
Activate for: real-time communication, WebSocket connections, Socket.io, live updates, push notifications.
<!-- LEVEL 1 END -->

<!-- LEVEL 2 START -->
## Core Instructions

1. **Choose Wisely**: WebSocket for bidirectional, SSE for server-push only, polling as last resort.
2. **Handle Reconnection**: Always implement exponential backoff reconnection logic.
3. **Heartbeat**: Use ping/pong to detect dead connections. Close after 3 missed heartbeats.
4. **Authenticate**: Validate tokens on connection, not just HTTP. Re-validate periodically.
5. **Scale Right**: Use Redis adapter for multi-server. Configure sticky sessions for Socket.io.

### Quick Checklist
- [ ] Reconnection logic with backoff
- [ ] Heartbeat/ping-pong implemented
- [ ] Authentication on connection
- [ ] Rooms/namespaces for organization
- [ ] Error handling and cleanup
<!-- LEVEL 2 END -->

<!-- LEVEL 3 START -->
## Full Reference

### WebSocket vs SSE vs Long-Polling

| Technology | Direction | Use Case | Overhead |
|------------|-----------|----------|----------|
| WebSocket | Bidirectional | Chat, gaming, collab | Low after handshake |
| SSE | Server → Client | News feed, notifications | Very low |
| Long-Polling | Bidirectional | Legacy fallback | High |

```
Choose WebSocket when:
- Need bidirectional real-time communication
- High frequency updates (chat, gaming)
- Low latency critical

Choose SSE when:
- Only server needs to push data
- Simpler implementation preferred
- News feeds, notifications, dashboards
```

### Socket.io Implementation

```javascript
// Server (Node.js)
const { Server } = require('socket.io');

const io = new Server(httpServer, {
  cors: { origin: '*' },
  pingTimeout: 60000,
  pingInterval: 25000,
});

// Authentication middleware
io.use(async (socket, next) => {
  const token = socket.handshake.auth.token;
  try {
    const user = await verifyToken(token);
    socket.user = user;
    next();
  } catch (err) {
    next(new Error('Authentication failed'));
  }
});

io.on('connection', (socket) => {
  console.log(`User ${socket.user.id} connected`);

  // Join user's personal room
  socket.join(`user:${socket.user.id}`);

  // Handle events
  socket.on('message', (data) => {
    io.to(`chat:${data.chatId}`).emit('message', data);
  });

  socket.on('disconnect', (reason) => {
    console.log(`Disconnected: ${reason}`);
  });
});

// Namespaces for organization
const chatNamespace = io.of('/chat');
chatNamespace.on('connection', (socket) => {
  socket.on('join-room', (roomId) => {
    socket.join(roomId);
    socket.to(roomId).emit('user-joined', socket.user);
  });
});
```

```javascript
// Client
import { io } from 'socket.io-client';

const socket = io('http://localhost:3000', {
  auth: { token: getAuthToken() },
  reconnection: true,
  reconnectionAttempts: 10,
  reconnectionDelay: 1000,
  reconnectionDelayMax: 5000,
});

socket.on('connect', () => {
  console.log('Connected:', socket.id);
});

socket.on('message', (data) => {
  displayMessage(data);
});

socket.on('disconnect', (reason) => {
  if (reason === 'io server disconnect') {
    // Server disconnected, don't reconnect automatically
    socket.connect();
  }
});

socket.on('connect_error', (error) => {
  console.error('Connection error:', error);
});
```

### Rooms and Namespaces

```javascript
// Rooms - for grouping within a namespace
io.to('room-1').emit('event', data);
socket.join('room-1');
socket.leave('room-1');

// Broadcast to all except sender
socket.to('room-1').emit('event', data);

// Namespaces - for separating concerns
const adminNamespace = io.of('/admin');
const chatNamespace = io.of('/chat');

// Client connects to namespace
const adminSocket = io('/admin');
const chatSocket = io('/chat');
```

### Connection Lifecycle

```javascript
// Server-side lifecycle
io.on('connection', (socket) => {
  // 1. Connection established
  console.log('Connected:', socket.id);

  // 2. Join rooms
  socket.join('general');

  // 3. Handle events
  socket.on('custom-event', handler);

  // 4. Handle errors
  socket.on('error', (err) => {
    console.error('Socket error:', err);
  });

  // 5. Cleanup on disconnect
  socket.on('disconnect', () => {
    // Clean up resources
    clearInterval(socket.heartbeatInterval);
  });
});
```

### Heartbeat/Ping-Pong

```javascript
// Socket.io has built-in heartbeat
const io = new Server(httpServer, {
  pingInterval: 25000,  // Send ping every 25s
  pingTimeout: 60000,  // Wait 60s for pong
});

// Custom heartbeat for native WebSocket
const WebSocket = require('ws');
const wss = new WebSocket.Server({ server });

wss.on('connection', (ws) => {
  ws.isAlive = true;

  ws.on('pong', () => {
    ws.isAlive = true;
  });

  // Heartbeat check interval
  const interval = setInterval(() => {
    wss.clients.forEach((ws) => {
      if (!ws.isAlive) {
        return ws.terminate();
      }
      ws.isAlive = false;
      ws.ping();
    });
  }, 30000);

  ws.on('close', () => {
    clearInterval(interval);
  });
});
```

### Reconnection Logic

```javascript
// Client reconnection with exponential backoff
class WebSocketClient {
  constructor(url) {
    this.url = url;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 10;
    this.baseDelay = 1000;
    this.maxDelay = 30000;
    this.connect();
  }

  connect() {
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      console.log('Connected');
      this.reconnectAttempts = 0;
    };

    this.ws.onclose = (event) => {
      if (event.code !== 1000) {
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      return;
    }

    const delay = Math.min(
      this.baseDelay * Math.pow(2, this.reconnectAttempts),
      this.maxDelay
    );

    console.log(`Reconnecting in ${delay}ms...`);
    setTimeout(() => {
      this.reconnectAttempts++;
      this.connect();
    }, delay);
  }
}
```

### Scaling WebSockets

```javascript
// Redis adapter for Socket.io (multi-server)
const { createAdapter } = require('@socket.io/redis-adapter');
const { createClient } = require('redis');

const pubClient = createClient({ url: 'redis://localhost:6379' });
const subClient = pubClient.duplicate();

io.adapter(createAdapter(pubClient, subClient));

// Now events are synced across all servers
// Server A emits -> Server B receives
io.to('room-1').emit('event', data);
```

```nginx
# Nginx sticky sessions for WebSocket
upstream socket_io {
    ip_hash;  # Sticky sessions
    server server1:3000;
    server server2:3000;
}

server {
    location /socket.io/ {
        proxy_pass http://socket_io;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

### Authentication Over WebSocket

```javascript
// Initial auth on connection
io.use(async (socket, next) => {
  const token = socket.handshake.auth.token;
  const user = await verifyToken(token);
  if (!user) return next(new Error('Unauthorized'));
  socket.user = user;
  next();
});

// Periodic re-authentication
const AUTH_CHECK_INTERVAL = 5 * 60 * 1000; // 5 minutes

io.on('connection', (socket) => {
  const authInterval = setInterval(async () => {
    const isValid = await verifyUserSession(socket.user.id);
    if (!isValid) {
      socket.emit('auth-expired');
      socket.disconnect(true);
    }
  }, AUTH_CHECK_INTERVAL);

  socket.on('disconnect', () => {
    clearInterval(authInterval);
  });
});
```
<!-- LEVEL 3 END -->