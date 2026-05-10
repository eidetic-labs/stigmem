#!/usr/bin/env node
/**
 * stigmem/adapters/paperclip/emit-fact.js
 *
 * CLI helper for Paperclip hooks and skill invocations to read/write Stigmem facts.
 *
 * Commands:
 *   assert   — POST /v1/facts
 *   query    — GET /v1/facts
 *   retract  — POST /v1/facts with confidence=0.0
 *
 * Usage:
 *   node emit-fact.js assert --entity <e> --relation <r> --value <json> --source <s> [--scope <s>] [--confidence <n>]
 *   node emit-fact.js query  [--entity <e>] [--relation <r>] [--scope <s>] [--limit <n>]
 *   node emit-fact.js retract --entity <e> --relation <r> --scope <s> --source <s>
 *
 * Environment:
 *   STIGMEM_URL       — required
 *   STIGMEM_API_KEY   — optional
 */

"use strict";

const url = process.env.STIGMEM_URL;
if (!url) {
  console.error("Error: STIGMEM_URL not set");
  process.exit(1);
}

const apiKey = process.env.STIGMEM_API_KEY;

const headers = {
  "Content-Type": "application/json",
  Accept: "application/json",
  ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {}),
};

async function fetchJSON(method, path, body) {
  const fullUrl = `${url.replace(/\/$/, "")}${path}`;
  const res = await fetch(fullUrl, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({ detail: res.statusText }));
  if (!res.ok) {
    console.error(`HTTP ${res.status}: ${data.detail ?? JSON.stringify(data)}`);
    process.exit(1);
  }
  return data;
}

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i++) {
    if (argv[i].startsWith("--")) {
      const key = argv[i].slice(2);
      args[key] = argv[i + 1] ?? true;
      i++;
    }
  }
  return args;
}

const [, , command, ...rest] = process.argv;
const args = parseArgs(rest);

switch (command) {
  case "assert": {
    const { entity, relation, value, source, scope = "company", confidence = "1.0" } = args;
    if (!entity || !relation || !value || !source) {
      console.error("assert requires --entity --relation --value --source");
      process.exit(1);
    }
    let parsedValue;
    try {
      parsedValue = JSON.parse(value);
    } catch {
      console.error(`--value must be valid JSON, got: ${value}`);
      process.exit(1);
    }
    const fact = await fetchJSON("POST", "/v1/facts", {
      entity,
      relation,
      value: parsedValue,
      source,
      scope,
      confidence: parseFloat(confidence),
    });
    console.log(JSON.stringify(fact, null, 2));
    break;
  }

  case "retract": {
    const { entity, relation, scope, source } = args;
    if (!entity || !relation || !scope || !source) {
      console.error("retract requires --entity --relation --scope --source");
      process.exit(1);
    }
    const fact = await fetchJSON("POST", "/v1/facts", {
      entity,
      relation,
      value: { type: "string", v: "retracted" },
      source,
      scope,
      confidence: 0.0,
    });
    console.log(JSON.stringify(fact, null, 2));
    break;
  }

  case "query": {
    const { entity, relation, source, scope, min_confidence, limit = "50", cursor } = args;
    const params = new URLSearchParams({ limit });
    if (entity)         params.set("entity", entity);
    if (relation)       params.set("relation", relation);
    if (source)         params.set("source", source);
    if (scope)          params.set("scope", scope);
    if (min_confidence) params.set("min_confidence", min_confidence);
    if (cursor)         params.set("cursor", cursor);
    const page = await fetchJSON("GET", `/v1/facts?${params}`);
    console.log(JSON.stringify(page, null, 2));
    break;
  }

  default:
    console.error(`Unknown command: ${command}. Use assert | retract | query`);
    process.exit(1);
}
