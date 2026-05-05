import React, { useEffect, useState } from 'react';
import styles from './styles.module.css';

type Referrer = { href: string; label: string };

/**
 * Renders a "← Back to <previous page>" chip when the user arrived on this
 * page from a same-origin link. Reads `document.referrer` once on mount, so
 * the chip survives in-page navigation only as long as the browser keeps the
 * referrer header set. Clicking the chip is equivalent to history.back().
 *
 * Used by the swizzled DocItem/Content theme component on every docs page so
 * deep-linked targets (notably spec sections) always have a visible way back.
 */
export default function SiteBackLink() {
  const [referrer, setReferrer] = useState<Referrer | null>(null);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const raw = document.referrer;
    if (!raw) return;
    let url: URL;
    try {
      url = new URL(raw);
    } catch {
      return;
    }
    if (url.origin !== window.location.origin) return;
    if (url.pathname === window.location.pathname) return;

    const segments = url.pathname.split('/').filter(Boolean);
    const last = segments[segments.length - 1] ?? '';
    const label =
      last
        .replace(/-/g, ' ')
        .replace(/\b\w/g, (c) => c.toUpperCase()) || 'Previous page';
    setReferrer({ href: url.href, label });
  }, []);

  if (!referrer) return null;

  return (
    <a
      className={styles.backLink}
      href={referrer.href}
      onClick={(e) => {
        // Prefer history.back when possible — preserves scroll position.
        if (window.history.length > 1) {
          e.preventDefault();
          window.history.back();
        }
      }}
      aria-label={`Back to ${referrer.label}`}
    >
      <span aria-hidden="true">←</span> Back to {referrer.label}
    </a>
  );
}
