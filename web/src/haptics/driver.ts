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

// The mouse reports exactly 15 presets, 0-14 (read from its haptic feature's capabilities
// on 2026-11-21, docs/hardware-log.md). Some docs say 16; index 15 does not exist.
export const MAX_WAVEFORM_INDEX = 14

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
  /** False when this driver has no way to change how strong the vibration is. */
  readonly canSetStrength: boolean
  /** Vibration strength, 0 (off) to 100. Null when it cannot be read. */
  getStrength(): Promise<number | null>
  /**
   * Set vibration strength, 0 (off) to 100. This changes a setting on the mouse itself, so
   * call it when the user moves a control, not on every tick.
   */
  setStrength(percent: number): Promise<void>
}

function clampStrength(percent: number): number {
  return Math.min(100, Math.max(0, Math.round(percent)))
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
  // short = 14, chosen by Ananya Maheshwari on 2026-11-21 (the plugin names it square). It is
  // looped fast for the buzz of a shorted wire; not yet felt in the product.
  short: 14,
}

/** No hardware. Fires a window event so the UI can flash, and logs. */
export class ConsoleHaptics implements HapticsDriver {
  readonly name = 'console'
  readonly isConnected = true
  readonly canSetStrength = true
  private strength = 60
  async connect() {}
  close() {}
  async getStrength() {
    return this.strength
  }
  async setStrength(percent: number) {
    this.strength = clampStrength(percent)
  }
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
  // The plugin's API takes a waveform index and nothing else.
  readonly canSetStrength = false
  async getStrength() {
    return null
  }
  async setStrength() {
    throw new Error('The plugin driver cannot change strength; use webhid')
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
 * report 0x11, 19 bytes: device index, feature 0x0b4e, effect id, zeros.
 *
 * Two ways the mouse can be connected:
 *  - Bluetooth: the browser sees the mouse itself; device index 0x02, as in that project.
 *  - Logi Bolt USB receiver: the browser sees the receiver, and the device index is the
 *    slot the mouse is paired to (1-6). We find the slot by pinging each one.
 * TODO(haptics owner): the receiver route is our own guess at the addressing, not from
 * any Logitech doc. Confirm on the real mouse and log it in docs/hardware-log.md.
 */
interface HidCollection {
  usagePage?: number
  outputReports?: { reportId?: number }[]
}
interface HidInputReportEvent {
  reportId: number
  data: DataView
}
interface HidDevice {
  opened: boolean
  productId: number
  productName: string
  collections: HidCollection[]
  open(): Promise<void>
  close(): Promise<void>
  sendReport(reportId: number, data: Uint8Array): Promise<void>
  addEventListener(type: 'inputreport', listener: (event: HidInputReportEvent) => void): void
  removeEventListener(type: 'inputreport', listener: (event: HidInputReportEvent) => void): void
}
interface Hid {
  requestDevice(options: {
    filters: { vendorId: number; productId: number }[]
  }): Promise<HidDevice[]>
}

const LOGITECH = 0x046d
const MOUSE_PRODUCT_IDS = [0xb042, 0xb048] // MX Master 4 and the Business edition, over Bluetooth
/** Said when the device picker is closed without choosing: the person changed their mind, which
 *  is not a fault, so the page shows nothing for it. */
export const PICKER_CLOSED = 'No mouse was selected'
const BOLT_RECEIVER_PRODUCT_ID = 0xc548
const LONG_REPORT = 0x11
const LONG_REPORT_BYTES = 19
const BLUETOOTH_DEVICE_INDEX = 0x02
const RECEIVER_SLOTS = [1, 2, 3, 4, 5, 6]
const REPLY_TIMEOUT_MS = 300
const PING_MARK = 0xa5
const SOFTWARE_ID = 0x0e // any non-zero value; replies echo it so we can match them
// HID++ feature 0x19b0 (haptics) sits at index 0x0b on the MX Master 4. Its functions, from
// the Solaar project and checked on the real mouse: 0 capabilities, 1 read enabled + strength,
// 2 write enabled + strength, 4 play preset. No function for custom waveforms is known.
const HAPTIC_FEATURE_INDEX = 0x0b
const FN_PING = 1
const FN_GET_STRENGTH = 1
const FN_SET_STRENGTH = 2
const FN_PLAY = 4

export class WebHidHaptics implements HapticsDriver {
  readonly name = 'webhid'
  private device: HidDevice | null = null
  private deviceIndex = BLUETOOTH_DEVICE_INDEX

  get isConnected() {
    return this.device?.opened === true
  }

  async connect() {
    const hid = (navigator as Navigator & { hid?: Hid }).hid
    if (!hid) throw new Error('WebHID is not available in this browser')
    const devices = await hid.requestDevice({
      filters: [...MOUSE_PRODUCT_IDS, BOLT_RECEIVER_PRODUCT_ID].map((productId) => ({
        vendorId: LOGITECH,
        productId,
      })),
    })
    // A receiver shows up as several HID devices; only one of them takes the long report.
    const device =
      devices.find((candidate) =>
        candidate.collections.some((collection) =>
          collection.outputReports?.some((report) => report.reportId === LONG_REPORT),
        ),
      ) ?? devices[0]
    if (!device) throw new Error(PICKER_CLOSED)
    if (!device.opened) await device.open()
    this.device = device

    if (device.productId === BOLT_RECEIVER_PRODUCT_ID) {
      const slot = await this.findReceiverSlot(device)
      if (slot === null) {
        throw new Error(
          'The receiver is connected but no mouse answered. Is the mouse on and on the receiver channel?',
        )
      }
      this.deviceIndex = slot
      console.log(`haptics: mouse found on receiver slot ${slot}`)
    } else {
      this.deviceIndex = BLUETOOTH_DEVICE_INDEX
    }
  }

  /** Ping each pairing slot (HID++ root feature) and return the first that echoes back. */
  private async findReceiverSlot(device: HidDevice): Promise<number | null> {
    for (const slot of RECEIVER_SLOTS) {
      const reply = await this.request(device, slot, 0x00, FN_PING, [0x00, 0x00, PING_MARK])
      if (reply && reply[2] === PING_MARK) return slot
    }
    return null
  }

  /**
   * Send one HID++ call and wait for its reply. Returns the reply's parameter bytes, or null
   * if the device answered with an error or did not answer in time.
   */
  private request(
    device: HidDevice,
    deviceIndex: number,
    featureIndex: number,
    fn: number,
    params: number[] = [],
  ): Promise<Uint8Array | null> {
    const call = (fn << 4) | SOFTWARE_ID
    return new Promise((resolve) => {
      const onReport = (event: HidInputReportEvent) => {
        const bytes = event.data
        if (bytes.byteLength < 4 || bytes.getUint8(0) !== deviceIndex) return
        const replyFeature = bytes.getUint8(1)
        if (replyFeature === featureIndex && bytes.getUint8(2) === call) {
          finish(new Uint8Array(bytes.buffer, bytes.byteOffset + 3, bytes.byteLength - 3))
        } else if (
          // 0xff marks an error reply to this feature; 0x8f is the older form.
          (replyFeature === 0xff && bytes.getUint8(2) === featureIndex) ||
          replyFeature === 0x8f
        ) {
          finish(null)
        }
      }
      const timer = setTimeout(() => finish(null), REPLY_TIMEOUT_MS)
      const finish = (result: Uint8Array | null) => {
        clearTimeout(timer)
        device.removeEventListener('inputreport', onReport)
        resolve(result)
      }
      device.addEventListener('inputreport', onReport)
      const data = new Uint8Array(LONG_REPORT_BYTES)
      data.set([deviceIndex, featureIndex, call, ...params])
      device.sendReport(LONG_REPORT, data).catch(() => finish(null))
    })
  }

  readonly canSetStrength = true
  async getStrength() {
    if (!this.device) return null
    const reply = await this.request(
      this.device,
      this.deviceIndex,
      HAPTIC_FEATURE_INDEX,
      FN_GET_STRENGTH,
    )
    if (!reply) return null
    const enabled = (reply[0] & 0x01) === 1
    return enabled ? reply[1] : 0
  }
  async setStrength(percent: number) {
    if (!this.device) throw new Error('Connect the mouse first')
    const level = clampStrength(percent)
    // Zero means "haptics off"; the mouse still wants a level, so park it at 50.
    const params = level === 0 ? [0x00, 50] : [0x01, level]
    const reply = await this.request(
      this.device,
      this.deviceIndex,
      HAPTIC_FEATURE_INDEX,
      FN_SET_STRENGTH,
      params,
    )
    if (!reply) throw new Error('The mouse did not accept the strength change')
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
    const data = new Uint8Array(LONG_REPORT_BYTES)
    data.set([this.deviceIndex, HAPTIC_FEATURE_INDEX, (FN_PLAY << 4) | SOFTWARE_ID, index])
    // A failed report must not become an unhandled rejection in the middle of a tick stream.
    this.device
      ?.sendReport(LONG_REPORT, data)
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
