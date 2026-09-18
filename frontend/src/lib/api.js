const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function getJSON(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `${res.status} ${res.statusText}`);
  }
  return res.json();
}

async function postJSON(path, payload) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `${res.status} ${res.statusText}`);
  }
  return res.json();
}

export function listRings({ minScore = 0, limit = 50, offset = 0 } = {}) {
  const params = new URLSearchParams({ min_score: minScore, limit, offset });
  return getJSON(`/rings?${params}`);
}

export function getRing(ringId, { nodeLimit = 300 } = {}) {
  const params = new URLSearchParams({ node_limit: nodeLimit });
  return getJSON(`/rings/${encodeURIComponent(ringId)}?${params}`);
}

export function getAccount(accountId, { neighborLimit = 100 } = {}) {
  const params = new URLSearchParams({ neighbor_limit: neighborLimit });
  return getJSON(`/account/${encodeURIComponent(accountId)}?${params}`);
}

export function getGraph({ ringId, accountId, hops = 1, minScore = 0.3, limit = 300 } = {}) {
  const params = new URLSearchParams({ hops, min_score: minScore, limit });
  if (ringId) params.set("ring_id", ringId);
  if (accountId) params.set("account_id", accountId);
  return getJSON(`/graph?${params}`);
}

export function getScoreSamples() {
  return getJSON("/score/samples");
}

export function scoreSample(sampleId) {
  return postJSON("/score", { sample_id: sampleId });
}

export function scoreFields(fields) {
  return postJSON("/score", { fields });
}
