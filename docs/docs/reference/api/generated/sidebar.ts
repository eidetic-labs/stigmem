import type { SidebarsConfig } from "@docusaurus/plugin-content-docs";

const sidebar: SidebarsConfig = {
  apisidebar: [
    {
      type: "doc",
      id: "reference/api/generated/stigmem-reference-node",
    },
    {
      type: "category",
      label: "discovery",
      items: [
        {
          type: "doc",
          id: "reference/api/generated/node-metadata-well-known-stigmem-get",
          label: "Node Metadata",
          className: "api-method get",
        },
      ],
    },
    {
      type: "category",
      label: "ops",
      items: [
        {
          type: "doc",
          id: "reference/api/generated/health-healthz-get",
          label: "Health",
          className: "api-method get",
        },
      ],
    },
    {
      type: "category",
      label: "admin",
      items: [
        {
          type: "doc",
          id: "reference/api/generated/admin-audit-export-v-1-admin-audit-get",
          label: "Admin Audit Export",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "reference/api/generated/cid-backfill-status-v-1-admin-cid-backfill-status-get",
          label: "Cid Backfill Status",
          className: "api-method get",
        },
      ],
    },
    {
      type: "category",
      label: "cid",
      items: [
        {
          type: "doc",
          id: "reference/api/generated/cid-backfill-status-v-1-admin-cid-backfill-status-get",
          label: "Cid Backfill Status",
          className: "api-method get",
        },
      ],
    },
    {
      type: "category",
      label: "aliases",
      items: [
        {
          type: "doc",
          id: "reference/api/generated/list-aliases-v-1-aliases-get",
          label: "List Aliases",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "reference/api/generated/create-alias-v-1-aliases-post",
          label: "Create Alias",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "reference/api/generated/delete-alias-v-1-aliases-raw-uri-delete",
          label: "Delete Alias",
          className: "api-method delete",
        },
      ],
    },
    {
      type: "category",
      label: "audit",
      items: [
        {
          type: "doc",
          id: "reference/api/generated/query-audit-v-1-audit-get",
          label: "Query Audit",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "reference/api/generated/export-audit-csv-v-1-audit-export-get",
          label: "Export Audit Csv",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "reference/api/generated/get-fact-audit-v-1-audit-facts-fact-id-get",
          label: "Get Fact Audit",
          className: "api-method get",
        },
      ],
    },
    {
      type: "category",
      label: "auth",
      items: [
        {
          type: "doc",
          id: "reference/api/generated/list-agent-keys-v-1-auth-agent-keys-get",
          label: "List Agent Keys",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "reference/api/generated/register-agent-key-v-1-auth-agent-keys-post",
          label: "Register Agent Key",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "reference/api/generated/revoke-agent-key-v-1-auth-agent-keys-key-id-delete",
          label: "Revoke Agent Key",
          className: "api-method delete",
        },
        {
          type: "doc",
          id: "reference/api/generated/list-keys-v-1-auth-keys-get",
          label: "List Keys",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "reference/api/generated/register-static-key-v-1-auth-keys-post",
          label: "Register a caller-provided static API key (admin only).",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "reference/api/generated/list-expiring-keys-v-1-auth-keys-expiring-soon-get",
          label: "List Expiring Keys",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "reference/api/generated/revoke-key-v-1-auth-keys-key-id-delete",
          label: "Revoke Key",
          className: "api-method delete",
        },
        {
          type: "doc",
          id: "reference/api/generated/oidc-exchange-v-1-auth-oidc-exchange-post",
          label: "Oidc Exchange",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "reference/api/generated/whoami-v-1-me-get",
          label: "Whoami",
          className: "api-method get",
        },
      ],
    },
    {
      type: "category",
      label: "cards",
      items: [
        {
          type: "doc",
          id: "reference/api/generated/get-card-v-1-cards-entity-uri-get",
          label: "Get Card",
          className: "api-method get",
        },
      ],
    },
    {
      type: "category",
      label: "federation",
      items: [
        {
          type: "doc",
          id: "reference/api/generated/list-conflicts-v-1-conflicts-get",
          label: "List Conflicts",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "reference/api/generated/resolve-conflict-v-1-conflicts-conflict-id-resolve-post",
          label: "Resolve Conflict",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "reference/api/generated/get-audit-log-v-1-federation-audit-get",
          label: "Get Audit Log",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "reference/api/generated/pull-facts-v-1-federation-facts-get",
          label: "Pull Facts",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "reference/api/generated/push-facts-v-1-federation-facts-push-post",
          label: "Push Facts",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "reference/api/generated/list-peers-v-1-federation-peers-get",
          label: "List Peers",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "reference/api/generated/register-peer-v-1-federation-peers-post",
          label: "Register Peer",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "reference/api/generated/approve-peer-v-1-federation-peers-peer-id-approve-post",
          label: "Approve Peer",
          className: "api-method post",
        },
      ],
    },
    {
      type: "category",
      label: "decay",
      items: [
        {
          type: "doc",
          id: "reference/api/generated/get-decay-job-v-1-decay-jobs-job-id-get",
          label: "Get Decay Job",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "reference/api/generated/decay-sweep-v-1-decay-sweep-post",
          label: "Decay Sweep",
          className: "api-method post",
        },
      ],
    },
    {
      type: "category",
      label: "entities",
      items: [
        {
          type: "doc",
          id: "reference/api/generated/resolve-entity-uri-v-1-entities-resolve-get",
          label: "Resolve Entity Uri",
          className: "api-method get",
        },
      ],
    },
    {
      type: "category",
      label: "facts",
      items: [
        {
          type: "doc",
          id: "reference/api/generated/query-facts-v-1-facts-get",
          label: "Query Facts",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "reference/api/generated/assert-fact-v-1-facts-post",
          label: "Assert Fact",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "reference/api/generated/get-fact-v-1-facts-fact-id-get",
          label: "Get Fact",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "reference/api/generated/get-provenance-v-1-facts-fact-id-provenance-get",
          label: "Get Provenance",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "reference/api/generated/verify-cid-v-1-facts-fact-id-verify-cid-post",
          label: "Verify Cid",
          className: "api-method post",
        },
      ],
    },
    {
      type: "category",
      label: "identity",
      items: [
        {
          type: "doc",
          id: "reference/api/generated/issue-capability-token-v-1-federation-capability-tokens-post",
          label: "Issue Capability Token",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "reference/api/generated/verify-capability-token-endpoint-v-1-federation-capability-tokens-verify-post",
          label: "Verify Capability Token Endpoint",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "reference/api/generated/revoke-capability-token-v-1-federation-capability-tokens-token-id-revoke-post",
          label: "Revoke Capability Token",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "reference/api/generated/put-manifest-v-1-federation-manifest-put",
          label: "Put Manifest",
          className: "api-method put",
        },
        {
          type: "doc",
          id: "reference/api/generated/get-manifest-v-1-federation-manifest-entity-uri-encoded-get",
          label: "Get Manifest",
          className: "api-method get",
        },
      ],
    },
    {
      type: "category",
      label: "gardens",
      items: [
        {
          type: "doc",
          id: "reference/api/generated/list-gardens-v-1-gardens-get",
          label: "List Gardens",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "reference/api/generated/create-garden-v-1-gardens-post",
          label: "Create Garden",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "reference/api/generated/delete-garden-v-1-gardens-garden-slug-or-id-delete",
          label: "Delete Garden",
          className: "api-method delete",
        },
        {
          type: "doc",
          id: "reference/api/generated/get-garden-v-1-gardens-garden-slug-or-id-get",
          label: "Get Garden",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "reference/api/generated/list-members-v-1-gardens-garden-slug-or-id-members-get",
          label: "List Members",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "reference/api/generated/add-member-v-1-gardens-garden-slug-or-id-members-post",
          label: "Add Member",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "reference/api/generated/remove-member-v-1-gardens-garden-slug-or-id-members-entity-uri-delete",
          label: "Remove Member",
          className: "api-method delete",
        },
        {
          type: "doc",
          id: "reference/api/generated/update-member-role-v-1-gardens-garden-slug-or-id-members-entity-uri-patch",
          label: "Update Member Role",
          className: "api-method patch",
        },
        {
          type: "doc",
          id: "reference/api/generated/promote-fact-v-1-gardens-garden-slug-or-id-promote-post",
          label: "Promote Fact",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "reference/api/generated/reject-fact-v-1-gardens-garden-slug-or-id-reject-post",
          label: "Reject Fact",
          className: "api-method post",
        },
      ],
    },
    {
      type: "category",
      label: "graph",
      items: [
        {
          type: "doc",
          id: "reference/api/generated/graph-neighbors-v-1-graph-neighbors-get",
          label: "Graph Neighbors",
          className: "api-method get",
        },
      ],
    },
    {
      type: "category",
      label: "intents",
      items: [
        {
          type: "doc",
          id: "reference/api/generated/submit-intent-v-1-intents-post",
          label: "Submit Intent",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "reference/api/generated/get-intent-v-1-intents-intent-id-get",
          label: "Get Intent",
          className: "api-method get",
        },
      ],
    },
    {
      type: "category",
      label: "lint",
      items: [
        {
          type: "doc",
          id: "reference/api/generated/lint-scope-v-1-lint-post",
          label: "Lint Scope",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "reference/api/generated/get-lint-job-v-1-lint-jobs-job-id-get",
          label: "Get Lint Job",
          className: "api-method get",
        },
      ],
    },
    {
      type: "category",
      label: "quarantine",
      items: [
        {
          type: "doc",
          id: "reference/api/generated/list-quarantined-facts-v-1-quarantine-get",
          label: "List Quarantined Facts",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "reference/api/generated/admit-fact-v-1-quarantine-fact-id-admit-post",
          label: "Admit Fact",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "reference/api/generated/reject-fact-v-1-quarantine-fact-id-reject-post",
          label: "Reject Fact",
          className: "api-method post",
        },
      ],
    },
    {
      type: "category",
      label: "recall",
      items: [
        {
          type: "doc",
          id: "reference/api/generated/recall-v-1-recall-post",
          label: "Recall",
          className: "api-method post",
        },
      ],
    },
    {
      type: "category",
      label: "synthesis",
      items: [
        {
          type: "doc",
          id: "reference/api/generated/synthesize-scope-v-1-scopes-scope-synthesize-get",
          label: "Synthesize Scope",
          className: "api-method get",
        },
      ],
    },
    {
      type: "category",
      label: "subscriptions",
      items: [
        {
          type: "doc",
          id: "reference/api/generated/list-subscriptions-v-1-subscriptions-get",
          label: "List Subscriptions",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "reference/api/generated/create-subscription-v-1-subscriptions-post",
          label: "Create Subscription",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "reference/api/generated/delete-subscription-v-1-subscriptions-subscription-id-delete",
          label: "Delete Subscription",
          className: "api-method delete",
        },
        {
          type: "doc",
          id: "reference/api/generated/get-subscription-v-1-subscriptions-subscription-id-get",
          label: "Get Subscription",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "reference/api/generated/list-subscription-events-v-1-subscriptions-subscription-id-events-get",
          label: "List Subscription Events",
          className: "api-method get",
        },
      ],
    },
  ],
};

export default sidebar.apisidebar;
