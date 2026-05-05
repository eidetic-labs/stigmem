import React from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import styles from './index.module.css';

function HomepageHeader(): JSX.Element {
  const { siteConfig } = useDocusaurusContext();
  return (
    <header className={clsx('hero hero--primary', styles.heroBanner)}>
      <div className="container">
        <img
          src="img/logo.svg"
          alt="Stigmem logo"
          className={styles.heroLogo}
        />
        <h1 className="hero__title">{siteConfig.title}</h1>
        <p className="hero__subtitle">{siteConfig.tagline}</p>
        <div className={styles.buttons}>
          <Link className="button button--secondary button--lg" to="/docs/learn/quickstart/quickstart-tutorial">
            Quickstart — under 5 minutes →
          </Link>
          <Link className="button button--outline button--secondary button--lg" to="/docs/learn/quickstart">
            Getting Started
          </Link>
        </div>
      </div>
    </header>
  );
}

type FeatureItem = {
  title: string;
  description: string;
};

const features: FeatureItem[] = [
  {
    title: 'Structured facts',
    description:
      'Every piece of knowledge is an immutable (entity, relation, value) triple with provenance, confidence score, scope, and a hybrid logical clock timestamp — so every memory is auditable and reproducible.',
  },
  {
    title: 'Federated by design',
    description:
      'Facts replicate across peer nodes via Ed25519-signed tokens and scope-enforced pull replication. Conflicts surface as first-class objects and are never silently discarded.',
  },
  {
    title: 'Plugs into your stack',
    description:
      'Native connectors for Claude Code, Cursor, Zed, Gemini, Codex CLI, and LiteLLM. Your agents share a verifiable memory in minutes — no custom glue code required.',
  },
  {
    title: 'Interactive API reference',
    description:
      'Auto-generated from the OpenAPI schema. Try live requests against your local node directly from the docs.',
  },
];

export default function Home(): JSX.Element {
  const { siteConfig } = useDocusaurusContext();
  return (
    <Layout title={siteConfig.title} description={siteConfig.tagline}>
      <HomepageHeader />
      <main>
        <div className="container">
          <div className={clsx('row', styles.featureRow)}>
            {features.map(({ title, description }) => (
              <div key={title} className="col col--3">
                <h3>{title}</h3>
                <p>{description}</p>
              </div>
            ))}
          </div>
        </div>
      </main>
    </Layout>
  );
}
