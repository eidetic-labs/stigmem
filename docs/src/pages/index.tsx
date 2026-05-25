import { Fragment, useEffect, useRef, useState } from 'react';
import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';

import styles from './index.module.css';

/* ──────────────────────────────────────────────────────────────────────────
 * FACT RECORDER — animated typing of a fact assert + federation replication
 *
 * Mirrors the operator's actual journey:
 *   1. Local agent asserts a typed fact at node-a
 *   2. Federation pull replicates the record to node-b under scope rules
 *   3. A recall query at node-b returns the fact + provenance
 *
 * Respects prefers-reduced-motion (renders the final frame immediately).
 * Disconnects the IntersectionObserver once primed.
 * ────────────────────────────────────────────────────────────────────────── */

type ScriptEntry = {
  cmd: string;
  comment: string | null;
  kind?: 'assert' | 'replicate' | 'recall' | 'idle';
};

const RECORDER_SCRIPT: ScriptEntry[] = [
  {
    cmd: 'curl -X POST http://node-a:8765/v1/facts \\',
    comment: null,
    kind: 'assert',
  },
  {
    cmd: '  -d \'{"entity":"user:alice", "relation":"memory:prefers",',
    comment: null,
    kind: 'assert',
  },
  {
    cmd: '      "value":{"type":"string","v":"dark mode"},',
    comment: null,
    kind: 'assert',
  },
  {
    cmd: '      "source":"agent:settings", "confidence":1.0,',
    comment: null,
    kind: 'assert',
  },
  {
    cmd: '      "scope":"company", "valid_until":"2026-12-31"}\'',
    comment: '→ accepted · fact_8f3c · hlc 7BFA0:42 · sig: ed25519',
    kind: 'assert',
  },
  {
    cmd: '# 30s later — node-b pulls scope=company from node-a',
    comment: '→ replicated · 1 record · peer node-a (verified)',
    kind: 'replicate',
  },
  {
    cmd: 'curl http://node-b:8766/v1/facts?entity=user:alice',
    comment: null,
    kind: 'recall',
  },
  {
    cmd: '',
    comment: '→ "dark mode" · source agent:settings · scope company',
    kind: 'recall',
  },
];

function FactRecorder() {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const [armed, setArmed] = useState(false);
  const [done, setDone] = useState(false);
  const [progress, setProgress] = useState({ line: 0, char: 0, showComment: false });

  useEffect(() => {
    if (armed || !rootRef.current) return undefined;
    if (
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    ) {
      setArmed(true);
      setDone(true);
      return undefined;
    }
    if (typeof IntersectionObserver === 'undefined') {
      setArmed(true);
      return undefined;
    }
    const obs = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setArmed(true);
          obs.disconnect();
        }
      },
      { threshold: 0.25 },
    );
    obs.observe(rootRef.current);
    return () => obs.disconnect();
  }, [armed]);

  useEffect(() => {
    if (!armed || done) return undefined;
    const current = RECORDER_SCRIPT[progress.line];
    if (!current) return undefined;

    let id: ReturnType<typeof setTimeout> | undefined;
    if (progress.char < current.cmd.length) {
      const nextChar = current.cmd[progress.char];
      const isSpace = nextChar === ' ';
      const isComment = current.cmd.startsWith('#');
      const delay = isComment ? 14 : isSpace ? 24 + Math.random() * 22 : 28 + Math.random() * 36;
      id = setTimeout(() => {
        setProgress({ line: progress.line, char: progress.char + 1, showComment: false });
      }, delay);
    } else if (current.comment && !progress.showComment) {
      id = setTimeout(() => {
        setProgress({ line: progress.line, char: progress.char, showComment: true });
      }, 300);
    } else if (progress.line < RECORDER_SCRIPT.length - 1) {
      const isBoundary =
        RECORDER_SCRIPT[progress.line + 1]?.kind !== current.kind;
      id = setTimeout(
        () => {
          setProgress({ line: progress.line + 1, char: 0, showComment: false });
        },
        isBoundary ? 820 : 320,
      );
    } else {
      setDone(true);
    }
    return () => {
      if (id) clearTimeout(id);
    };
  }, [armed, done, progress]);

  const visibleCount = done ? RECORDER_SCRIPT.length : progress.line + 1;

  return (
    <article ref={rootRef} className={styles.recorder} aria-label="Stigmem fact assert + recall demo">
      <header className={styles.recorderChrome}>
        <div className={styles.recorderDots}>
          <span className={`${styles.recorderDot} ${styles.recorderDotR}`} />
          <span className={`${styles.recorderDot} ${styles.recorderDotY}`} />
          <span className={`${styles.recorderDot} ${styles.recorderDotG}`} />
        </div>
        <span className={styles.recorderPath}>node-a · scope=company · fact_record</span>
        <span className={styles.recorderHlc}>HLC 7BFA0:42</span>
      </header>
      <div className={styles.recorderBody} aria-live="polite">
        {RECORDER_SCRIPT.slice(0, visibleCount).map((entry, i) => {
          const isCurrent = !done && i === progress.line;
          const text = isCurrent ? entry.cmd.slice(0, progress.char) : entry.cmd;
          const showCaret = isCurrent;
          const commentVisible = done
            ? !!entry.comment
            : isCurrent
              ? progress.showComment && !!entry.comment
              : !!entry.comment;
          const isHashLine = entry.cmd.startsWith('#');
          const kindClass =
            entry.kind === 'assert'
              ? styles.recorderKindAssert
              : entry.kind === 'replicate'
                ? styles.recorderKindReplicate
                : entry.kind === 'recall'
                  ? styles.recorderKindRecall
                  : '';
          const previousLineContinues =
            i > 0 && RECORDER_SCRIPT[i - 1]?.cmd.endsWith('\\');
          return (
            <Fragment key={i}>
              {!isHashLine && entry.cmd && (
                <p className={`${styles.recorderLine} ${kindClass}`}>
                  {previousLineContinues ? (
                    <span className={styles.recorderPromptCont}>·</span>
                  ) : (
                    <span className={styles.recorderPrompt}>$</span>
                  )}{' '}
                  <span className={styles.recorderText}>{text}</span>
                  {showCaret && <span className={styles.recorderCaret}>▌</span>}
                </p>
              )}
              {isHashLine && entry.cmd && (
                <p className={`${styles.recorderLine} ${styles.recorderHashLine}`}>
                  <span className={styles.recorderText}>{text}</span>
                  {showCaret && <span className={styles.recorderCaret}>▌</span>}
                </p>
              )}
              {commentVisible && entry.comment && (
                <p className={`${styles.recorderComment} ${kindClass}`}>{entry.comment}</p>
              )}
            </Fragment>
          );
        })}
        {done && (
          <p className={styles.recorderLine}>
            <span className={styles.recorderPrompt}>$</span> <span className={styles.recorderCaret}>▌</span>
          </p>
        )}
      </div>
    </article>
  );
}

/* ──────────────────────────────────────────────────────────────────────────
 * FEDERATION DIAGRAM — two nodes exchanging a PeerDeclaration handshake
 * ────────────────────────────────────────────────────────────────────────── */

function FederationDiagram() {
  return (
    <figure className={styles.federation} aria-label="Federation handshake between two Stigmem nodes">
      <svg
        viewBox="0 0 540 270"
        xmlns="http://www.w3.org/2000/svg"
        className={styles.federationSvg}
        aria-hidden="true"
      >
        <defs>
          <linearGradient id="stig-handshake" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#818cf8" stopOpacity="0.2" />
            <stop offset="50%" stopColor="#a78bfa" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#818cf8" stopOpacity="0.2" />
          </linearGradient>
          <marker id="stig-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
            <path d="M 0 0 L 10 5 L 0 10 z" className={styles.federationArrowHead} />
          </marker>
        </defs>

        <g className={styles.federationGrid} strokeWidth="1" fill="none">
          <line x1="0" y1="60" x2="540" y2="60" />
          <line x1="0" y1="125" x2="540" y2="125" />
          <line x1="0" y1="190" x2="540" y2="190" />
        </g>

        {/* Handshake line — center between the two nodes */}
        <line
          x1="160"
          y1="125"
          x2="380"
          y2="125"
          stroke="url(#stig-handshake)"
          strokeWidth="2"
          strokeDasharray="6 8"
          className={styles.federationHandshake}
        />

        {/* Replication arcs */}
        <path
          d="M 160 109 Q 270 81 380 109"
          fill="none"
          strokeWidth="1.4"
          strokeDasharray="3 4"
          markerEnd="url(#stig-arrow)"
          className={styles.federationReplA}
        />

        <path
          d="M 380 141 Q 270 169 160 141"
          fill="none"
          strokeWidth="1.4"
          strokeDasharray="3 4"
          markerEnd="url(#stig-arrow)"
          className={styles.federationReplB}
        />

        {/* Node A: circle, name inside, scope + HLC stacked below */}
        <g className={styles.federationNode}>
          <circle cx="130" cy="125" r="44" className={styles.federationNodeCircle} strokeWidth="1.6" />
          <text x="130" y="130" textAnchor="middle" className={styles.federationNodeName}>node-a</text>
          <text x="130" y="200" textAnchor="middle" className={styles.federationNodeScope}>scope: company</text>
          <text x="130" y="222" textAnchor="middle" className={styles.federationHlc}>HLC 7BFA0:42</text>
        </g>

        {/* Node B: same structure, scope string is longer so it gets full width below the circle */}
        <g className={styles.federationNode}>
          <circle cx="410" cy="125" r="44" className={styles.federationNodeCircle} strokeWidth="1.6" />
          <text x="410" y="130" textAnchor="middle" className={styles.federationNodeName}>node-b</text>
          <text x="410" y="200" textAnchor="middle" className={styles.federationNodeScope}>scope: company, public</text>
          <text x="410" y="222" textAnchor="middle" className={styles.federationHlc}>HLC 7BFA0:43</text>
        </g>

        {/* PeerDeclaration chip — widened to fit full label */}
        <g>
          <rect
            x="165"
            y="20"
            width="210"
            height="26"
            rx="13"
            className={styles.federationChip}
            strokeWidth="1"
          />
          <text x="270" y="37" textAnchor="middle" dominantBaseline="middle" className={styles.federationLabel}>
            PeerDeclaration · ed25519
          </text>
        </g>
      </svg>
      <figcaption className={styles.federationCaption}>
        Two nodes peer via a signed handshake. Facts pull-replicate under explicit scope permission;
        contradictions surface as first-class records, never silently overwritten.
      </figcaption>
    </figure>
  );
}

/* ──────────────────────────────────────────────────────────────────────────
 * STATIC DATA
 * ────────────────────────────────────────────────────────────────────────── */

const PRIMITIVES = [
  {
    label: 'fact_record',
    type: '(entity, relation, value, source, ts, confidence, scope)',
    blurb:
      'Immutable typed records with full provenance, an HLC timestamp, and a defined expiry. The atomic unit of every Stigmem operation.',
  },
  {
    label: 'peer_declaration',
    type: 'ed25519-signed',
    blurb:
      'Signed handshake that establishes federation between two nodes. Defines which scopes the peer may pull and how often.',
  },
  {
    label: 'contradiction',
    type: 'first_class_record',
    blurb:
      'When two facts conflict, the contradiction surfaces as its own queryable record instead of one fact silently overwriting the other.',
  },
];

const PLUGINS = [
  {
    id: 'multi-tenant',
    pip: 'stigmem-plugin-multi-tenant',
    title: 'Multi-tenant scoping',
    blurb:
      'Boot context, handoff, decision, and escalation become tenant-scoped on the node side. Foundation for shared deployments.',
    to: '/docs/plugins/multi-tenant',
  },
  {
    id: 'source-attestation',
    pip: 'stigmem-plugin-source-attestation',
    title: 'Source attestation',
    blurb:
      'Recalled facts carry source trust scores. Low-trust sources can be filtered or quarantined by the node before reaching agents.',
    to: '/docs/plugins/source-attestation',
  },
  {
    id: 'memory-garden-acl',
    pip: 'stigmem-plugin-memory-garden-acl',
    title: 'Memory garden ACL',
    blurb:
      'Membership controls which gardens the boot handshake reads from. Per-operator access boundaries on a shared substrate.',
    to: '/docs/plugins/memory-garden-acl',
  },
  {
    id: 'tombstones',
    pip: 'stigmem-plugin-tombstones',
    title: 'Tombstones',
    blurb:
      'Hide retracted facts from recall and boot context. Audit-clean revocation without rewriting history.',
    to: '/docs/plugins/tombstones',
  },
  {
    id: 'time-travel',
    pip: 'stigmem-plugin-time-travel',
    title: 'Time travel',
    blurb:
      'Historical handoff and decision queries against the node. Replay what an agent knew at a specific HLC.',
    to: '/docs/plugins/time-travel',
  },
  {
    id: 'lazy-instruction-discovery',
    pip: 'stigmem-plugin-lazy-instruction-discovery',
    title: 'Lazy instruction discovery',
    blurb:
      'Boot context resolves instructions on-demand instead of eagerly. Smaller boot payloads, faster cold-start.',
    to: '/docs/plugins/lazy-instruction-discovery',
  },
];

const EDITORS = [
  { name: 'Codex CLI', tier: 'Validated', to: '/docs/integrations/mcp/codex-cli' },
  { name: 'Claude Code', tier: 'Validated', to: '/docs/integrations/mcp/claude-code' },
  { name: 'Gemini CLI', tier: 'Caveated', to: '/docs/integrations/mcp/gemini-cli' },
  { name: 'Continue.dev', tier: 'Experimental', to: '/docs/integrations/mcp/continue-dev' },
  { name: 'Cursor', tier: 'Experimental', to: '/docs/integrations/mcp/cursor' },
  { name: 'Zed', tier: 'Experimental', to: '/docs/integrations/mcp/zed' },
];

/* ──────────────────────────────────────────────────────────────────────────
 * SMALL COMPONENTS
 * ────────────────────────────────────────────────────────────────────────── */

function Arrow({ size = 14 }: { size?: number }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} aria-hidden="true">
      <path
        d="M5 12h14M13 5l7 7-7 7"
        stroke="currentColor"
        strokeWidth="2"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function PulseDot() {
  return <span className={styles.eyebrowDot} aria-hidden="true" />;
}

/* ──────────────────────────────────────────────────────────────────────────
 * PAGE
 * ────────────────────────────────────────────────────────────────────────── */

export default function Home() {
  return (
    <Layout
      title="Stigmem — federated knowledge fabric for AI agents"
      description="A federated, scope-aware knowledge fabric where AI agents and humans write typed, traceable facts that travel across tools, platforms, and organizations."
    >
      <main className={styles.home}>
        {/* ─────────── Hero ─────────── */}
        <section className={styles.hero} aria-labelledby="stig-hero-title">
          <div className={styles.heroBg} aria-hidden="true">
            <div className={styles.heroGlow} />
            <div className={styles.heroGrid} />
          </div>

          <div className={styles.heroCopy}>
            <p className={styles.eyebrow}>
              <PulseDot />
              v0.9.0a9 · preview alpha · Apache-2.0
            </p>
            <h1 id="stig-hero-title" className={styles.heroTitle}>
              <span className={styles.heroLine}>Shared, scope-aware</span>
              <span className={`${styles.heroLine} ${styles.heroLineAccent}`}>
                memory for agents.
              </span>
            </h1>
            <p className={styles.heroLede}>
              Stigmem is a federated knowledge fabric where AI agents and humans write typed,
              traceable facts that travel across tools, platforms, and organizations. Every
              fact is an immutable record with full provenance, a hybrid logical clock
              timestamp, and a defined expiry. Nodes peer via signed handshakes; replication
              respects scope; contradictions never silently overwrite.
            </p>

            <div className={styles.heroActions}>
              <Link className={`${styles.button} ${styles.buttonPrimary}`} to="/docs/get-started/quickstart-tutorial">
                <span>Quickstart</span>
                <Arrow />
              </Link>
              <Link className={`${styles.button} ${styles.buttonGhost}`} to="/docs/concepts/overview">
                <span>Read the model</span>
              </Link>
              <code className={styles.heroSnippet}>
                <span className={styles.heroSnippetPrompt}>$</span>
                <span>docker compose up -d</span>
              </code>
            </div>

            <dl className={styles.heroStats}>
              <div>
                <dt>Surface</dt>
                <dd>federated · scope-enforced</dd>
              </div>
              <div>
                <dt>Plugins</dt>
                <dd>6 on PyPI · independent versioning</dd>
              </div>
              <div>
                <dt>Integrations</dt>
                <dd>MCP · 6 editor hosts</dd>
              </div>
            </dl>
          </div>

          <aside className={styles.heroStage} aria-label="Anatomy of a Stigmem fact record">
            <div className={styles.factCard}>
              <div className={styles.factCardChrome}>
                <span className={styles.factCardLabel}>fact_record</span>
                <span className={styles.factCardId}>fact_8f3c</span>
              </div>
              <ol className={styles.factCardFields}>
                <li>
                  <span className={styles.factFieldKey}>entity</span>
                  <span className={styles.factFieldVal}>"user:alice"</span>
                </li>
                <li>
                  <span className={styles.factFieldKey}>relation</span>
                  <span className={styles.factFieldVal}>"memory:prefers"</span>
                </li>
                <li>
                  <span className={styles.factFieldKey}>value</span>
                  <span className={styles.factFieldVal}>{'{"type":"string","v":"dark mode"}'}</span>
                </li>
                <li>
                  <span className={styles.factFieldKey}>source</span>
                  <span className={styles.factFieldVal}>"agent:settings"</span>
                </li>
                <li>
                  <span className={styles.factFieldKey}>timestamp</span>
                  <span className={styles.factFieldVal}>hlc 7BFA0:42</span>
                </li>
                <li>
                  <span className={styles.factFieldKey}>confidence</span>
                  <span className={styles.factFieldVal}>1.0</span>
                </li>
                <li>
                  <span className={styles.factFieldKey}>scope</span>
                  <span className={styles.factFieldVal}>"company"</span>
                </li>
                <li>
                  <span className={styles.factFieldKey}>valid_until</span>
                  <span className={styles.factFieldVal}>2026-12-31T23:59Z</span>
                </li>
              </ol>
              <div className={styles.factCardSig}>
                sig · ed25519 · <span className={styles.factCardSigVal}>3f2a 8e11 ··· d4c9</span>
              </div>
            </div>
          </aside>
        </section>

        {/* ─────────── Primitives band ─────────── */}
        <section className={styles.primitives} aria-labelledby="stig-primitives-title">
          <header className={styles.sectionHead}>
            <p className={styles.eyebrow}>
              <span className={styles.eyebrowNum}>§</span> Primitives
            </p>
            <h2 id="stig-primitives-title">Three durable, typed objects.</h2>
            <p className={styles.sectionLede}>
              Everything in Stigmem composes from these. Each is queryable, signed, and
              bound to a node + scope.
            </p>
          </header>
          <ul className={styles.primitiveGrid} role="list">
            {PRIMITIVES.map((p) => (
              <li key={p.label} className={styles.primitive}>
                <p className={styles.primitiveLabel}>{p.label}</p>
                <p className={styles.primitiveType}>{p.type}</p>
                <p className={styles.primitiveBlurb}>{p.blurb}</p>
              </li>
            ))}
          </ul>
        </section>

        {/* ─────────── Fact recorder demo ─────────── */}
        <section className={styles.demo} aria-labelledby="stig-demo-title">
          <header className={styles.sectionHead}>
            <p className={styles.eyebrow}>
              <span className={styles.eyebrowNum}>§</span> Demo
            </p>
            <h2 id="stig-demo-title">Assert a fact. Replicate. Recall.</h2>
            <p className={styles.sectionLede}>
              The full operator loop in one terminal. Watch a fact land on node-a, replicate
              under scope to node-b, and return on a recall — with provenance attached at
              every step.
            </p>
          </header>
          <div className={styles.demoBody}>
            <FactRecorder />
            <aside className={styles.demoSide}>
              <h3>What just happened</h3>
              <ol className={styles.demoSteps}>
                <li>
                  <span className={styles.demoStepNum}>01</span>
                  <div>
                    <strong>Assert</strong>
                    <p>
                      A typed fact lands at node-a with an Ed25519-signed provenance trail and a
                      hybrid logical clock timestamp.
                    </p>
                  </div>
                </li>
                <li>
                  <span className={styles.demoStepNum}>02</span>
                  <div>
                    <strong>Replicate</strong>
                    <p>
                      Node-b pulls scope=company on a configurable interval. The record arrives
                      with its signature intact and verifiable.
                    </p>
                  </div>
                </li>
                <li>
                  <span className={styles.demoStepNum}>03</span>
                  <div>
                    <strong>Recall</strong>
                    <p>
                      A query at node-b returns the fact with source, scope, and HLC preserved.
                      No silent merging, no data loss.
                    </p>
                  </div>
                </li>
              </ol>
              <Link className={`${styles.button} ${styles.buttonGhost}`} to="/docs/get-started/quickstart-tutorial">
                <span>Run the full quickstart</span>
                <Arrow />
              </Link>
            </aside>
          </div>
        </section>

        {/* ─────────── Federation diagram ─────────── */}
        <section className={styles.federationSection} aria-labelledby="stig-fed-title">
          <header className={`${styles.sectionHead} ${styles.sectionHeadSplit}`}>
            <div>
              <p className={styles.eyebrow}>
                <span className={styles.eyebrowNum}>§</span> Federation
              </p>
              <h2 id="stig-fed-title">Two nodes. One signed handshake.</h2>
            </div>
            <p className={styles.sectionLede}>
              Stigmem nodes federate via PeerDeclarations — Ed25519-signed records that
              establish which scopes a peer may pull. Replication is explicit, audited, and
              scoped. The cost of a peering decision is contained in the record.
            </p>
          </header>
          <FederationDiagram />
        </section>

        {/* ─────────── Plugin grid ─────────── */}
        <section className={styles.plugins} aria-labelledby="stig-plugins-title">
          <header className={styles.sectionHead}>
            <p className={styles.eyebrow}>
              <span className={styles.eyebrowNum}>§</span> Plugins
            </p>
            <h2 id="stig-plugins-title">Six published plugins. Independent versioning.</h2>
            <p className={styles.sectionLede}>
              Plugins extend node behavior without modifying the protocol. Each is its own
              PyPI package on its own release cadence. Install one, all, or none — the
              substrate works the same.
            </p>
          </header>
          <ul className={styles.pluginGrid} role="list">
            {PLUGINS.map((p) => (
              <li key={p.id}>
                <Link className={styles.pluginCard} to={p.to}>
                  <p className={styles.pluginPip}>{p.pip}</p>
                  <h3 className={styles.pluginTitle}>{p.title}</h3>
                  <p className={styles.pluginBlurb}>{p.blurb}</p>
                  <span className={styles.pluginCta}>
                    Read <Arrow size={12} />
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </section>

        {/* ─────────── Editor integrations ─────────── */}
        <section className={styles.editors} aria-labelledby="stig-editors-title">
          <header className={styles.sectionHead}>
            <p className={styles.eyebrow}>
              <span className={styles.eyebrowNum}>§</span> Editor integrations
            </p>
            <h2 id="stig-editors-title">MCP server. Six editor hosts.</h2>
            <p className={styles.sectionLede}>
              Stigmem ships an MCP server so LLM-aware editors can read and write to a node
              directly. Validation tier reflects the depth of host UI smoke evidence on file.
            </p>
          </header>
          <ul className={styles.editorList} role="list">
            {EDITORS.map((e) => {
              const tierClass =
                e.tier === 'Validated'
                  ? styles.tierValidated
                  : e.tier === 'Caveated'
                    ? styles.tierCaveated
                    : styles.tierExperimental;
              return (
                <li key={e.name}>
                  <Link className={styles.editorRow} to={e.to}>
                    <span className={styles.editorName}>{e.name}</span>
                    <span className={`${styles.editorTier} ${tierClass}`}>{e.tier}</span>
                    <span className={styles.editorArrow}>
                      <Arrow size={12} />
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </section>

        {/* ─────────── Honest status ─────────── */}
        <section className={styles.status} aria-labelledby="stig-status-title">
          <div className={styles.statusBox}>
            <p className={styles.eyebrow}>
              <PulseDot />
              Honest status
            </p>
            <h2 id="stig-status-title">
              Pre-stable. Read <code>LIMITATIONS.md</code> before integrating.
            </h2>
            <p className={styles.statusLede}>
              Stigmem is at <code>v0.9.0a9</code> — a preview alpha. Single-org, single-node
              deployments are the currently-supported pattern. Cross-org federation needs
              hardened-core work documented in the roadmap. The version label matches the
              validated stability posture; there is no v1.0 yet, and the implied chronology
              of earlier markers (<code>v0.2</code> through <code>v2.0</code>) was reset.
            </p>
            <div className={styles.statusActions}>
              <Link className={`${styles.button} ${styles.buttonGhost}`} to="https://github.com/eidetic-labs/stigmem/blob/main/LIMITATIONS.md">
                <span>LIMITATIONS.md</span>
                <Arrow />
              </Link>
              <Link className={`${styles.button} ${styles.buttonGhost}`} to="https://github.com/eidetic-labs/stigmem/blob/main/SECURITY.md">
                <span>SECURITY.md</span>
                <Arrow />
              </Link>
              <Link className={`${styles.button} ${styles.buttonGhost}`} to="https://dev.to/offbyonce/walking-back-our-v10-announcement-resetting-to-v090a1-as-the-first-build-al0">
                <span>Why v0.9.0a1</span>
                <Arrow />
              </Link>
            </div>
          </div>
        </section>

        {/* ─────────── Footer band ─────────── */}
        <section className={styles.band} aria-labelledby="stig-band-title">
          <div>
            <p className={styles.eyebrow}>
              <PulseDot />
              Eidetic Labs
            </p>
            <h2 id="stig-band-title">Spec, source, community.</h2>
            <p className={styles.bandLede}>
              The specification is the source of truth. The repository carries the reference
              node, the SDKs, and the conformance suite. The Discord is where adopters,
              contributors, and operators discuss installation, federation, and the spec.
            </p>
          </div>
          <div className={styles.bandActions}>
            <Link className={`${styles.button} ${styles.buttonPrimary}`} to="/docs/spec">
              <span>Read the spec</span>
              <Arrow />
            </Link>
            <Link className={`${styles.button} ${styles.buttonGhost}`} to="https://github.com/eidetic-labs/stigmem">
              <span>github · eidetic-labs/stigmem</span>
            </Link>
            <Link className={`${styles.button} ${styles.buttonGhost}`} to="https://discord.gg/Z47Re7FjjV">
              <span>discord</span>
            </Link>
            <Link className={`${styles.button} ${styles.buttonGhost}`} to="https://pypi.org/project/stigmem/">
              <span>pypi · stigmem</span>
            </Link>
          </div>
        </section>
      </main>
    </Layout>
  );
}
