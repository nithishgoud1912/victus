"""Read-only DOM helpers; bookkeeping stays in page memory, never attributes."""

# Each document has its own token. Mutation/input counters conservatively require
# reobservation; they are freshness evidence, not protection from a malicious site.
DOM_HELPERS = r"""
const key = Symbol.for('victus.observation.v1');
let state = window[key];
if (!state) {
    state = {document: String(Date.now()) + Math.random(), revision: 0,
             nodes: new WeakMap(), next: 0};
    state.observer = new MutationObserver(records => {state.revision += records.length;});
    state.observer.observe(document, {subtree: true, childList: true,
                                     characterData: true, attributes: true});
    for (const event of ['input', 'change'])
        document.addEventListener(event, () => {state.revision++;}, true);
    window[key] = state;
}
state.revision += state.observer.takeRecords().length;
const stamp = () => ({document: state.document, revision: state.revision, url: location.href});
const visible = el => {
    // Playwright CSS selectors pierce open shadow roots; this increment does not.
    if (!el || !el.isConnected || el.getRootNode() !== document) return false;
    for (let node = el; node && node.nodeType === 1; node = node.parentElement) {
        const css = getComputedStyle(node);
        if (node.hidden || node.inert || node.getAttribute('aria-hidden') === 'true' ||
            css.display === 'none' || ['hidden', 'collapse'].includes(css.visibility) ||
            Number(css.opacity) === 0 || css.contentVisibility === 'hidden') return false;
    }
    return el.getClientRects().length > 0;
};
const sensitive = el => {
    const control = el.closest('input,textarea');
    return !!el.closest('input[type="password" i], input[type="hidden" i]') ||
        !!control && (control.autocomplete || '').toLowerCase().split(/\s+/)
            .some(token => ['current-password', 'new-password', 'one-time-code'].includes(token));
};
const hiddenLabel = el => {
    const labels = [...(el.labels || [])];
    for (const id of (el.getAttribute('aria-labelledby') || '').split(/\s+/).filter(Boolean)) {
        const label = document.getElementById(id);
        if (!label) return true;
        labels.push(label);
    }
    for (const label of labels) {
        if (!visible(label)) return true;
        const walker = document.createTreeWalker(label, NodeFilter.SHOW_TEXT);
        let node, visited = 0;
        while ((node = walker.nextNode())) {
            if (++visited > 500) return true;
            if (node.textContent.trim() && !visible(node.parentElement)) return true;
        }
    }
    return false;
};
const nodeId = el => {
    if (!state.nodes.has(el)) state.nodes.set(el, ++state.next);
    return state.nodes.get(el);
};
const describe = el => ({
    node: nodeId(el), tag: el.tagName.toLowerCase(), type: el.type || '',
    role: el.getAttribute('role') || '', id: el.id, name: el.getAttribute('name') || '',
    href: el.tagName === 'A' ? el.href : '',
    visible: visible(el), sensitive: sensitive(el),
    disabled: el.matches(':disabled') || el.getAttribute('aria-disabled') === 'true',
    readonly: !!el.readOnly || el.getAttribute('aria-readonly') === 'true',
    editable: el.isContentEditable,
    // Do not use hidden referenced content to advertise an accessible name.
    hiddenLabel: hiddenLabel(el)
});
"""

STAMP_SCRIPT = "() => {" + DOM_HELPERS + "return stamp();}"
DESCRIBE_SCRIPT = "el => {" + DOM_HELPERS + "return describe(el);}"

# No input values, textarea defaults, script/style/template content, or raw HTML.
# Limits bound DOM traversal and output rather than merely truncating an unbounded extraction.
TEXT_SCRIPT = (
    "limits => {"
    + DOM_HELPERS
    + r"""
const walker = document.createTreeWalker(document.body || document.documentElement,
    NodeFilter.SHOW_TEXT);
let result = '', visited = 0, node;
while ((node = walker.nextNode()) && visited++ < limits.max_nodes) {
    const parent = node.parentElement;
    if (!parent || !visible(parent) || sensitive(parent) ||
        parent.closest('script,style,template,noscript,textarea,select,[contenteditable]')) continue;
    const text = node.textContent.replace(/\s+/g, ' ').trim();
    if (!text) continue;
    result += (result ? ' ' : '') + text.slice(0, limits.max_chars - result.length);
    if (result.length >= limits.max_chars) break;
}
return result.slice(0, limits.max_chars);
}"""
)

CANDIDATES = (
    'button, a[href], input, textarea, select, [contenteditable="true"], '
    '[role="button"], [role="link"], [role="textbox"], [role="searchbox"], '
    '[role="checkbox"], [role="radio"], [role="combobox"], [role="spinbutton"]'
)
