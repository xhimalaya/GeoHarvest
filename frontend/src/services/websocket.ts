type MessageCallback = (data: any) => void

class WebSocketService {
  private ws: WebSocket | null = null
  private listeners: MessageCallback[] = []
  private reconnectTimer: any = null

  connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/ws`

    try {
      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        // Send keepalive ping periodically
        setInterval(() => {
          if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send('ping')
          }
        }, 15000)
      }

      this.ws.onmessage = (event) => {
        if (event.data === 'pong') return
        try {
          const data = JSON.parse(event.data)
          this.listeners.forEach((callback) => callback(data))
        } catch (e) {
          // Non-JSON message
        }
      }

      this.ws.onclose = () => {
        // Attempt reconnect after 3 seconds
        clearTimeout(this.reconnectTimer)
        this.reconnectTimer = setTimeout(() => this.connect(), 3000)
      }

      this.ws.onerror = () => {
        if (this.ws) {
          this.ws.close()
        }
      }
    } catch (e) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = setTimeout(() => this.connect(), 3000)
    }
  }

  addListener(callback: MessageCallback) {
    this.listeners.push(callback)
  }

  removeListener(callback: MessageCallback) {
    this.listeners = this.listeners.filter((cb) => cb !== callback)
  }
}

export const wsService = new WebSocketService()
