import React, { useEffect, useState } from 'react';
import styles from './styles.module.css';

type Referrer = { href: string; label: string };

const TITLE_KEY = 'stigmem-page-title';

function labelFromTitle(stored: string): string {
  return stored
    .replace(/\s*[|–—].*$/, '')
    .replace(/^\s*Stigmem\s*/i, '')
    .trim() || 'Previous page';
}

function labelFromPath(pathname: string): string {
  const segments = pathname.split('/').filter(Boolean);
  let slug = segments[segments.length - 1] ?? '';
  if (slug === 'index' || slug === '') {
    slug = segments[segments.length - 2] ?? '';
  }
  return slug
    .replace(/-/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase()) || 'Previous page';
}

export default function SiteBackLink() {
  const [referrer, setReferrer] = useState<Referrer | null>(null);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const prevTitle = sessionStorage.getItem(TITLE_KEY);
    sessionStorage.setItem(TITLE_KEY, document.title);

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

    const label = prevTitle ? labelFromTitle(prevTitle) : labelFromPath(url.pathname);
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
