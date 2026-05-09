import React from 'react';
import Admonition from '@theme/Admonition';
import Link from '@docusaurus/Link';

const STATUS_META: Record<string, { type: 'warning' | 'caution' | 'info'; label: string; anchor: string }> = {
  Experimental: { type: 'caution', label: 'Experimental', anchor: '#how-to-read-this-page' },
  Beta: { type: 'warning', label: 'Beta', anchor: '#how-to-read-this-page' },
  Planned: { type: 'info', label: 'Planned', anchor: '#how-to-read-this-page' },
};

export type FeatureStatusValue = keyof typeof STATUS_META;

export default function FeatureStatus({ status }: { status: FeatureStatusValue }) {
  const meta = STATUS_META[status];
  if (!meta) return null;
  return (
    <Admonition type={meta.type} title={`${meta.label} feature`}>
      This feature is <strong>{meta.label}</strong>. Breaking changes may occur
      before it reaches Stable.{' '}
      <Link to={`/docs/concepts/features${meta.anchor}`}>
        See feature status definitions →
      </Link>
    </Admonition>
  );
}
