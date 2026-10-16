import type { ReactNode } from "react"
export function AppShell({ children }: { children: ReactNode }) { return (
<div className="workspace">
      <aside className="sidebar" aria-label="Workspace identity">
        <a className="brand" href="/" aria-label="VICTUS home"><span className="brand-mark">V</span> VICTUS<span className="version">v1</span></a>
        <div className="sidebar-middle"><span className="eyebrow">YOUR WORKSPACE</span><div className="nav-current"><span aria-hidden="true">▦</span> Overview</div></div>
        <div className="sidebar-note"><span className="local-dot" /> Local by design<p>Your assistant.<br />On your computer.</p></div>
      </aside>
<main>{children}</main></div>
) }
