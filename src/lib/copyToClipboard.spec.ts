import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { copyToClipboard } from './copyToClipboard'

describe('copyToClipboard', () => {
  let isSecureContext = true
  let writeText = vi.fn().mockResolvedValue(undefined)
  let execCommand = vi.fn().mockReturnValue(true)

  beforeEach(() => {
    isSecureContext = true
    writeText = vi.fn().mockResolvedValue(undefined)
    execCommand = vi.fn().mockReturnValue(true)

    Object.defineProperty(window, 'isSecureContext', {
      configurable: true,
      get: () => isSecureContext,
    })

    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    })

    Object.defineProperty(document, 'execCommand', {
      configurable: true,
      value: execCommand,
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('uses clipboard API in secure context', async () => {
    const result = await copyToClipboard('hello')

    expect(result).toBe('copied')
    expect(writeText).toHaveBeenCalledWith('hello')
    expect(execCommand).not.toHaveBeenCalled()
  })

  it('falls back to execCommand when clipboard API is unavailable', async () => {
    isSecureContext = false
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: undefined,
    })

    const result = await copyToClipboard('hello')

    expect(result).toBe('copied')
    expect(execCommand).toHaveBeenCalledWith('copy')
  })

  it('falls back to execCommand when clipboard API throws', async () => {
    writeText.mockRejectedValue(new Error('denied'))

    const result = await copyToClipboard('hello')

    expect(result).toBe('copied')
    expect(execCommand).toHaveBeenCalledWith('copy')
  })

  it('selects element contents when copy fails and selectElement is provided', async () => {
    isSecureContext = false
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: undefined,
    })
    execCommand.mockReturnValue(false)

    const element = document.createElement('pre')
    element.textContent = 'payload'
    document.body.appendChild(element)

    const result = await copyToClipboard('payload', { selectElement: element })

    expect(result).toBe('selected')
    expect(window.getSelection()?.toString()).toBe('payload')

    document.body.removeChild(element)
  })

  it('returns failed when all strategies fail', async () => {
    isSecureContext = false
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: undefined,
    })
    execCommand.mockReturnValue(false)

    const result = await copyToClipboard('hello')

    expect(result).toBe('failed')
  })

  it('returns failed for empty text', async () => {
    const result = await copyToClipboard('')

    expect(result).toBe('failed')
    expect(writeText).not.toHaveBeenCalled()
    expect(execCommand).not.toHaveBeenCalled()
  })
})
