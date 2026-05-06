import type { SidebarsConfig } from "@docusaurus/plugin-content-docs";

const sidebar: SidebarsConfig = {
  apisidebar: [
    {
      type: "doc",
      id: "reference/api/generated/stigmem-reference-node",
    },
    {
      type: "category",
      label: "Facts",
      link: {
        type: "doc",
        id: "reference/api/generated/facts",
      },
      items: [
        {
          type: "doc",
          id: "reference/api/generated/assert-fact",
          label: "Assert a fact",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "reference/api/generated/query-facts",
          label: "Query facts",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "reference/api/generated/get-fact",
          label: "Get a single fact",
          className: "api-method get",
        },
      ],
    },
    {
      type: "category",
      label: "Federation",
      link: {
        type: "doc",
        id: "reference/api/generated/federation",
      },
      items: [
        {
          type: "doc",
          id: "reference/api/generated/register-peer",
          label: "Register a peer",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "reference/api/generated/list-peers",
          label: "List registered peers",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "reference/api/generated/federation-pull-facts",
          label: "Pull replication endpoint",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "reference/api/generated/federation-push-facts",
          label: "Push replication endpoint (optional)",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "reference/api/generated/get-federation-audit",
          label: "Federation audit log",
          className: "api-method get",
        },
      ],
    },
    {
      type: "category",
      label: "Conflicts",
      link: {
        type: "doc",
        id: "reference/api/generated/conflicts",
      },
      items: [
        {
          type: "doc",
          id: "reference/api/generated/list-conflicts",
          label: "List conflicts",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "reference/api/generated/resolve-conflict",
          label: "Resolve a conflict",
          className: "api-method post",
        },
      ],
    },
    {
      type: "category",
      label: "Node Metadata",
      link: {
        type: "doc",
        id: "reference/api/generated/node-metadata",
      },
      items: [
        {
          type: "doc",
          id: "reference/api/generated/get-well-known",
          label: "Node identity and capabilities",
          className: "api-method get",
        },
      ],
    },
    {
      type: "category",
      label: "Health",
      link: {
        type: "doc",
        id: "reference/api/generated/health",
      },
      items: [
        {
          type: "doc",
          id: "reference/api/generated/health-check",
          label: "Health check",
          className: "api-method get",
        },
      ],
    },
  ],
};

export default sidebar.apisidebar;
