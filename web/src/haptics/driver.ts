// One interface, three ways to reach the MX Master 4. The rest of the app only
// calls play(). Which waveform each pattern uses is decided here and nowhere else.
//
// Waveform indices are from the Haptic Web plugin docs (https://haptics.jmw.nz/api):
//   0 sharp_collision   1 sharp_state_change   2 knock        3 damp_collision
//   4 mad               5 ringing              6 subtle_collision   7 completed
//   8 jingle            9 damp_state_change   10 firework    11 happy_alert
//  12 wave             13 angry_alert         14 square
// TODO(haptics owner): feel all of them on the real mouse and tune this table.
// The WebHID effect ids (0..14) are NOT confirmed to follow the same order.
// Status 2026-11-21: webhid pulses fire (docs/hardware-log.md); plugin untested.

import type { HapticPattern } from '../contract'

// Index 15 is allowed because docs/roadmap.md and .claude/rules/hardware.md list presets 0-15.
// TODO(haptics owner): webhid is documented for 0-14 only; confirm 15 on the real mouse.
export const MAX_WAVEFORM_INDEX = 15

export interface HapticsDriver {
  readonly name: string
  /** True while pulses can reach the mouse. The console driver is always true. */
  readonly isConnected: boolean
  /** Must be called from a click: both real drivers need a user gesture. */
  connect(): Promise<void>
  /** Release the socket or HID device. Safe to call when not connected. */
  close(): void
  play(pattern: HapticPattern): void
  /** Fire one preset waveform by index (0 to MAX_WAVEFORM_INDEX). */
  playRaw(index: number): void
}

function assertWaveformIndex(index: number) {
  if (!Number.isInteger(index) || index < 0 || index > MAX_WAVEFORM_INDEX) {
    throw new RangeError(`Waveform index must be an integer 0 to ${MAX_WAVEFORM_INDEX}`)
  }
}

const WAVEFORM: Record<HapticPattern, number> = {
  // tick = 3, confirmed by feel on the real mouse via webhid (2026-11-21, Ananya Maheshwari).
  // The plugin names it damp_collision, but webhid ids are unconfirmed against those names.
  tick: 3,
  nudge: 2,
  short: 13,
  success: 7,
}

/** No hardware. Fires a window event so the UI can flash, and logs. */
export class ConsoleHaptics implements HapticsDriver {
  readonly name = 'console'
  readonly isConnected = true
  async connect() {}
  close() {}
  play(pattern: HapticPattern) {
    this.playRaw(WAVEFORM[pattern])
  }
  playRaw(index: number) {
    assertWaveformIndex(index)
    window.dispatchEvent(new CustomEvent('tacto:haptic', { detail: index }))
  }
}

/** Haptic Web plugin (needs Logi Options+ and the plugin from the Logi Marketplace). */
export class PluginHaptics implements HapticsDriver {
  readonly name = 'plugin'
  private socket: WebSocket | null = null

  get isConnected() {
    return this.socket?.readyState === WebSocket.OPEN
  }

  connect() {
    if (this.isConnected) return Promise.resolve()
    return new Promise<void>((resolve, reject) => {
      const socket = new WebSocket('wss://local.jmw.nz:41443/ws')
      socket.onopen = () => {
        this.socket = socket
        resolve()
      }
      socket.onerror = () => reject(new Error('Haptic Web plugin not reachable on :41443'))
      // Forget a socket the plugin dropped, so isConnected stays honest.
      socket.onclose = () => {
        if (this.socket === socket) this.socket = null
      }
    })
  }
  close() {
    this.socket?.close()
    this.socket = null
  }
  play(pattern: HapticPattern) {
    this.playRaw(WAVEFORM[pattern])
  }
  playRaw(index: number) {
    assertWaveformIndex(index)
    if (this.isConnected) this.socket!.send(new Uint8Array([index]))
    window.dispatchEvent(new CustomEvent('tacto:haptic', { detail: index }))
  }
}

/**
 * Direct WebHID, Chrome or Edge only. Packet layout follows
 * https://github.com/mario-gutierrez/mx-master-4-webhid (MIT):
 * report 0x11, 19 bytes: device index 0x02, feature 0x0b4e, effect id, zeros.
 */
interface HidDevice {
  opened: boolean
  open(): Promise<void>
  close(): Promise<void>
  sendReport(reportId: number, data: Uint8Array): Promise<void>
}
interface Hid {
  requestDevice(options: {
    filters: { vendorId: number; productId: number }[]
  }): Promise<HidDevice[]>
}

export class WebHidHaptics implements HapticsDriver {
  readonly name = 'webhid'
  private device: HidDevice | null = null

  get isConnected() {
    return this.device?.opened === true
  }

  async connect() {
    const hid = (navigator as Navigator & { hid?: Hid }).hid
    if (!hid) throw new Error('WebHID is not available in this browser')
    const [device] = await hid.requestDevice({
      filters: [
        { vendorId: 0x046d, productId: 0xb042 },
        { vendorId: 0x046d, productId: 0xb048 },
      ],
    })
    if (!device) throw new Error('No MX Master 4 selected')
    if (!device.opened) await device.open()
    this.device = device
  }
  close() {
    void this.device?.close()
    this.device = null
  }
  play(pattern: HapticPattern) {
    this.playRaw(WAVEFORM[pattern])
  }
  playRaw(index: number) {
    assertWaveformIndex(index)
    const data = new Uint8Array(19)
    data.set([0x02, 0x0b, 0x4e, index])
    // A failed report must not become an unhandled rejection in the middle of a tick stream.
    this.device
      ?.sendReport(0x11, data)
      .catch((error) => console.error('haptic report failed', error))
    window.dispatchEvent(new CustomEvent('tacto:haptic', { detail: index }))
  }
}

export const DRIVERS = {
  console: () => new ConsoleHaptics(),
  plugin: () => new PluginHaptics(),
  webhid: () => new WebHidHaptics(),
} satisfies Record<string, () => HapticsDriver>

export type DriverName = keyof typeof DRIVERS
