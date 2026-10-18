export function checklistItems(value: string): string[] {
  const items = value.replace(/\r\n/g, '\n').split('\n')
  if (!items.length || items.length > 50 || items.some(item => !item.trim() || /[\r\n]/.test(item) || Array.from(item).length > 160)) throw new Error('Enter 1–50 nonempty items, one per line, up to 160 characters each.')
  const text = 'Checklist\r\n' + items.map(item => '[ ] ' + item).join('\r\n') + '\r\n'
  if (Array.from(text).length > 4096 || new TextEncoder().encode(text).length > 8192) throw new Error('This checklist is too large. Shorten the items.')
  return items
}

