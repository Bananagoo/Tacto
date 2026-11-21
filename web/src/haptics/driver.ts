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

import type { HapticPattern } from '../contract'

export interface HapticsDriver {
  readonly name: string
  /** Must be called from a click: both real drivers need a user gesture. */
  connect(): Promise<void>
  play(pattern: HapticPattern): void
  playRaw(index: number): void
}

const WAVEFORM: Record<HapticPattern, number> = {
  tick: 6,
  nudge: 2,
  short: 13,
  success: 7,
}

/** No hardware. Fires a window event so the UI can flash, and logs. */
export class ConsoleHaptics implements HapticsDriver {
  readonly name = 'console'
  async connect() {}
  play(pattern: HapticPattern) {
    this.playRaw(WAVEFORM[pattern])
  }
  playRaw(index: number) {
    window.dispatchEvent(new CustomEvent('tacto:haptic', { detail: index }))
  }
}

/** Haptic Web plugin (needs Logi Options+ and the plugin from the Logi Marketplace). */
export class PluginHaptics implements HapticsDriver {
  readonly name = 'plugin'
  private socket: WebSocket | null = null

  connect() {
    return new Promise<void>((resolve, reject) => {
      const socket = new WebSocket('wss://local.jmw.nz:41443/ws')
      socket.onopen = () => {
        this.socket = socket
        resolve()
      }
      socket.onerror = () => reject(new Error('Haptic Web plugin not reachable on :41443'))
    })
  }
  play(pattern: HapticPattern) {
    this.playRaw(WAVEFORM[pattern])
  }
  playRaw(index: number) {
    if (this.socket?.readyState === WebSocket.OPEN) this.socket.send(new Uint8Array([index]))
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
  play(pattern: HapticPattern) {
    this.playRaw(WAVEFORM[pattern])
  }
  playRaw(index: number) {
    const data = new Uint8Array(19)
    data.set([0x02, 0x0b, 0x4e, index])
    void this.device?.sendReport(0x11, data)
    window.dispatchEvent(new CustomEvent('tacto:haptic', { detail: index }))
  }
}

export const DRIVERS = {
  console: () => new ConsoleHaptics(),
  plugin: () => new PluginHaptics(),
  webhid: () => new WebHidHaptics(),
} satisfies Record<string, () => HapticsDriver>

export type DriverName = keyof typeof DRIVERS
