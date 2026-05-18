import React, { useEffect, useState } from 'react';
import styles from './styles.module.css';

type Variant = 'star' | 'fork';

const REPO = 'eidetic-labs/stigmem';
const CACHE_KEY = `gh:${REPO}`;
const CACHE_TTL_MS = 60 * 60 * 1000; // 1h

const STAR_PATH =
  'M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z';
const FORK_PATH =
  'M5 5.372v.45c0 .98.626 1.84 1.554 2.143a3.751 3.751 0 0 0 1.946 2.502v1.566a2.501 2.501 0 1 0 1 0v-1.566a3.751 3.751 0 0 0 1.946-2.502A2.252 2.252 0 0 0 13 5.823v-.45M4.25 4.75a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Zm7.5 0a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3ZM8 14.25a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z';

function formatCount(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1).replace(/\.0$/, '') + 'M';
  if (n >= 1_000) return (n / 1_000).toFixed(1).replace(/\.0$/, '') + 'k';
  return String(n);
}

type Counts = { stars: number; forks: number };

let inflight: Promise<Counts | null> | null = null;

async function fetchCounts(): Promise<Counts | null> {
  if (typeof window === 'undefined') return null;

  // localStorage cache to avoid hammering GitHub API on every page load.
  try {
    const raw = window.localStorage.getItem(CACHE_KEY);
    if (raw) {
      const cached = JSON.parse(raw) as { stars: number; forks: number; ts: number };
      if (Date.now() - cached.ts < CACHE_TTL_MS) {
        return { stars: cached.stars, forks: cached.forks };
      }
    }
  } catch {
    /* ignore localStorage errors */
  }

  if (inflight) return inflight;

  inflight = (async () => {
    try {
      const res = await fetch(`https://api.github.com/repos/${REPO}`, {
        headers: { Accept: 'application/vnd.github+json' },
      });
      if (!res.ok) return null;
      const data = (await res.json()) as { stargazers_count: number; forks_count: number };
      const counts = { stars: data.stargazers_count, forks: data.forks_count };
      try {
        window.localStorage.setItem(
          CACHE_KEY,
          JSON.stringify({ ...counts, ts: Date.now() }),
        );
      } catch {
        /* ignore */
      }
      return counts;
    } catch {
      return null;
    } finally {
      inflight = null;
    }
  })();

  return inflight;
}

export default function GitHubButton({ variant }: { variant: Variant }) {
  const [count, setCount] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchCounts().then((c) => {
      if (cancelled || !c) return;
      setCount(variant === 'star' ? c.stars : c.forks);
    });
    return () => {
      cancelled = true;
    };
  }, [variant]);

  const label = variant === 'star' ? 'Star' : 'Fork';
  const href =
    variant === 'star'
      ? `https://github.com/${REPO}`
      : `https://github.com/${REPO}/fork`;
  const ariaLabel = variant === 'star' ? 'Star on GitHub' : 'Fork on GitHub';
  const path = variant === 'star' ? STAR_PATH : FORK_PATH;

  return (
    <a
      href={href}
      className={styles.pill}
      target="_blank"
      rel="noopener"
      aria-label={ariaLabel}
    >
      <svg
        className={styles.icon}
        viewBox="0 0 16 16"
        width="16"
        height="16"
        aria-hidden="true"
      >
        <path
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          d={path}
        />
      </svg>
      <span className={styles.label}>{label}</span>
      <span className={styles.count} aria-hidden={count === null}>
        {count === null ? '—' : formatCount(count)}
      </span>
    </a>
  );
}
