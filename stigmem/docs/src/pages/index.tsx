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
        <img src="img/logo.svg" alt="Stigmem logo" width={80} style={{ marginBottom: '1rem' }} />
        <h1 className="hero__title">{siteConfig.title}</h1>
        <p className="hero__subtitle">{siteConfig.tagline}</p>
        <div className={styles.buttons}>
          <Link className="button button--secondary button--lg" to="/docs/getting-started">
            Get started →
          </Link>
          <Link className="button button--outline button--secondary button--lg" to="/docs/api-reference">
            API Reference
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
      'Every piece of knowledge is an immutable (entity, relation, value) triple with provenance, confidence, scope, and a hybrid logical timestamp. See spec §2.',
  },
  {
    title: 'Federation',
    description:
      'Nodes replicate facts across a peer mesh using Ed25519-signed tokens and scope-enforced pull replication. Conflicts are first-class — never silently discarded. See spec §6.',
  },
  {
    title: 'Interactive API reference',
    description:
      'Auto-generated from the FastAPI OpenAPI schema. Try live requests against your local node from the docs. Run `npm run gen-api-docs` to refresh after a schema change.',
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
              <div key={title} className="col col--4">
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
