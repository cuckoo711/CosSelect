export type WsMessage =
  | { type: 'join_request'; participant_id: number; nickname: string }
  | { type: 'approval_result'; participant_id: number; nickname: string; status: string }
  | Record<string, any>

/**
 * Auto-reconnecting WebSocket for a space. Falls back silently if WS is
 * unavailable (callers should also keep a polling fallback).
 */
export class SpaceSocket {
  private ws: WebSocket | null = null
  private closed = false
  private retry = 0
  private timer: number | null = null

  constructor(
    private spaceId: string,
    private onMessage: (msg: WsMessage) => void,
  ) {}

  connect() {
    this.closed = false
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    const url = `${proto}://${location.host}/api/ws/${this.spaceId}`
    try {
      this.ws = new WebSocket(url)
    } catch {
      this.scheduleReconnect()
      return
    }
    this.ws.onopen = () => {
      this.retry = 0
    }
    this.ws.onmessage = (e) => {
      try {
        this.onMessage(JSON.parse(e.data))
      } catch {
        /* ignore malformed */
      }
    }
    this.ws.onclose = () => {
      if (!this.closed) this.scheduleReconnect()
    }
    this.ws.onerror = () => {
      this.ws?.close()
    }
  }

  private scheduleReconnect() {
    this.retry = Math.min(this.retry + 1, 6)
    const delay = Math.min(1000 * 2 ** this.retry, 15000)
    if (this.timer) window.clearTimeout(this.timer)
    this.timer = window.setTimeout(() => this.connect(), delay)
  }

  close() {
    this.closed = true
    if (this.timer) window.clearTimeout(this.timer)
    this.ws?.close()
    this.ws = null
  }
}
