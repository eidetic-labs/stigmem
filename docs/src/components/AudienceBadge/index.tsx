import React from 'react';
import styles from './styles.module.css';

const AUDIENCES = {
  Operator: { icon: '🔧', color: 'var(--audience-operator)' },
  Integrator: { icon: '🔌', color: 'var(--audience-integrator)' },
  Spec: { icon: '📐', color: 'var(--audience-spec)' },
} as const;

export type Audience = keyof typeof AUDIENCES;

export default function AudienceBadge({ audience }: { audience: Audience }) {
  const meta = AUDIENCES[audience];
  if (!meta) return null;
  return (
    <span
      className={styles.badge}
      style={{ '--badge-color': meta.color } as React.CSSProperties}
      aria-label={`Audience: ${audience}`}
    >
      <span aria-hidden="true">{meta.icon}</span> {audience}
    </span>
  );
}
