import { describe, expect, it } from 'vitest'
import { checklistItems } from './checklistInput'

describe('checklist input boundary', () => {
  it('preserves literal item text and normalizes only line separators', () => {
    expect(checklistItems('<img onerror=alert(1)>\r\n  preserve spacing  ')).toEqual(['<img onerror=alert(1)>', '  preserve spacing  '])
  })
  it('rejects empty, multiline-control and oversized inputs before admission', () => {
    for (const text of ['', 'a\n', '\t', 'a\rb', 'x'.repeat(161), Array(51).fill('item').join('\n'), Array(50).fill('x'.repeat(160)).join('\n')]) expect(() => checklistItems(text)).toThrow()
  })
  it('applies the total UTF-8 payload bound as well as character bounds', () => {
    expect(() => checklistItems(Array(30).fill('漢'.repeat(100)).join('\n'))).toThrow()
  })
})
