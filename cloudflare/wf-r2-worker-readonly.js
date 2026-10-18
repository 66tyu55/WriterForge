/**
 * WriterForge R2 read-only Worker, V67.
 * Deploy manually to the EXISTING wf-r2-api Worker; keep existing WF_R2 R2
 * binding and WF_API_TOKEN secret. No R2 writes, no raw bucket traversal.
 *
 * V69 adds strictly scoped read-only private-reading list and ranged content.\n * Existing /r2/object, /health,
 * /r2/status and /r2/inventory responses stay compatible with V66.
 */
const PREFIX = "writerforge/v1/";
const LIBRARY = "laocanyouji-25124";
const ROOT = PREFIX + "libraries/" + LIBRARY + "/";
const SHA = /^[0-9a-f]{64}$/;
const SMALL_MAX = 128 * 1024;
const BLOB_MAX = 256 * 1024 * 1024;
const CHUNK_MAX = 4 * 1024 * 1024;
const INVENTORY_PAGES = 10;
const PRIVATE_ROOT = PREFIX + "private-reading/";
const PRIVATE_FOLDERS = new Set(["single-works", "仙侠", "历史", "科幻"]);
const PRIVATE_LIST_LIMIT = 64;
const PRIVATE_MAX_KEY_BYTES = 1536;
const PRIVATE_ALLOWED_FILE = /\.(?:txt|md|epub|zip|rar|7z|pdf)$/i;


function json(value, status = 200) {
  return new Response(JSON.stringify(value), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
    },
  });
}
function fail(status, code) {
  return json({ ok: false, error: code }, status);
}
function sizeInt(s) {
  return typeof s === "string" && /^(0|[1-9][0-9]{0,11})$/.test(s)
    ? Number(s) : null;
}
async function authorized(request, secret) {
  if (typeof secret !== "string" || secret.length < 24) return false;
  const h = request.headers.get("Authorization") || "";
  if (!h.startsWith("Bearer ") || h.length > 8192) return false;
  const submitted = h.slice(7);
  const encoder = new TextEncoder();
  const [a, b] = await Promise.all([
    crypto.subtle.digest("SHA-256", encoder.encode(submitted)),
    crypto.subtle.digest("SHA-256", encoder.encode(secret)),
  ]);
  const x = new Uint8Array(a), y = new Uint8Array(b);
  let diff = 0;
  for (let i = 0; i < x.length; i++) diff |= x[i] ^ y[i];
  return diff === 0 && submitted.length === secret.length;
}
function allowedKey(key) {
  if (typeof key !== "string" || key.length > 250 || !key.startsWith(ROOT)) {
    return null;
  }
  if (key === ROOT + "latest.json") return "metadata";
  const suffix = key.slice(ROOT.length);
  if (/^snapshots\/[0-9a-f]{64}\.json$/.test(suffix)) return "metadata";
  if (/^blobs\/[0-9a-f]{64}$/.test(suffix)) return "blob";
  return null;
}
function allowedPrivateKey(key) {
  if (typeof key !== "string" || !key.startsWith(PRIVATE_ROOT) ||
      new TextEncoder().encode(key).length > PRIVATE_MAX_KEY_BYTES) {
    return null;
  }
  const path = key.slice(PRIVATE_ROOT.length);
  const parts = path.split("/");
  if (parts.length < 2 || !PRIVATE_FOLDERS.has(parts[0]) ||
      parts.some(x => !x || x === "." || x === ".." || /[\\\\\u0000-\u001f]/.test(x))) {
    return null;
  }
  // R2 zero-byte "folder marker" objects and executables are not source files.
  if (!PRIVATE_ALLOWED_FILE.test(parts[parts.length - 1])) return null;
  return "blob";
}
function privateListParams(url) {
  const pairs = [...url.searchParams.entries()];
  if (pairs.length > 2 || new Set(pairs.map(p => p[0])).size !== pairs.length ||
      pairs.some(p => !["folder", "cursor"].includes(p[0]))) return null;
  const folder = url.searchParams.get("folder");
  if (!PRIVATE_FOLDERS.has(folder)) return null;
  const cursor = url.searchParams.get("cursor");
  if (cursor !== null && (!cursor || cursor.length > 2048 ||
      /[\u0000-\u001f]/.test(cursor))) return null;
  return {folder, cursor};
}
async function privateList(env, url) {
  const p = privateListParams(url);
  if (!p) return fail(400, "WF_PRIVATE_LIST_QUERY_INVALID");
  const prefix = PRIVATE_ROOT + p.folder + "/";
  const started = performance.now();
  const result = await env.WF_R2.list({
    prefix, limit: PRIVATE_LIST_LIMIT,
    ...(p.cursor ? {cursor:p.cursor} : {}),
  });
  if (result.objects.length > PRIVATE_LIST_LIMIT ||
      (result.truncated && (!result.cursor || result.cursor === p.cursor))) {
    return fail(502, "WF_PRIVATE_LIST_CURSOR_INVALID");
  }
  const objects = [];
  for (const obj of result.objects) {
    if (typeof obj.key !== "string" || !obj.key.startsWith(prefix) ||
        !Number.isSafeInteger(obj.size) || obj.size < 0) {
      return fail(502, "WF_PRIVATE_LIST_OBJECT_INVALID");
    }
    // Folder marker entries are excluded, not miscounted as books.
    if (obj.key.endsWith("/") && obj.size === 0) continue;
    objects.push({
      key:obj.key, size:obj.size,
      etag:typeof obj.httpEtag === "string" ? obj.httpEtag : null,
      // Uploaded timestamps aid diagnostics; never infer the first upload date
      // without an earlier frozen inventory or independently signed records.
      uploaded:obj.uploaded instanceof Date ? obj.uploaded.toISOString() : null,
    });
  }
  return json({
    ok:true, read_only:true, format:"wf.private-reading-list.v1",
    folder:p.folder, objects,
    complete:!result.truncated,
    next_cursor:result.truncated ? result.cursor : null,
    page_entries:result.objects.length,
    elapsed_ms:Math.round(performance.now()-started),
  });
}

function objectHeaders(obj) {
  return {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Content-Type": "application/octet-stream",
    "X-WF-Object-Size": String(obj.size),
    "ETag": obj.httpEtag,
    "Accept-Ranges": "bytes",
  };
}
async function getObject(request, env, url, privateMode = false) {
  // Only the pinned single study library; no arbitrary paths or listing.
  const params = [...url.searchParams.keys()];
  if (params.length > 3 || params.some(k => !["key", "offset", "length"].includes(k)) ||
      new Set(params).size !== params.length) {
    return fail(400, "WF_OBJECT_QUERY_INVALID");
  }
  const key = url.searchParams.get("key");
  const kind = privateMode ? allowedPrivateKey(key) : allowedKey(key);
  if (!kind) return fail(403, "WF_OBJECT_OUTSIDE_PINNED_LIBRARY");
  const meta = await env.WF_R2.head(key);
  if (!meta) return fail(404, "WF_OBJECT_NOT_FOUND");
  const cap = kind === "blob" ? BLOB_MAX : SMALL_MAX;
  if (!Number.isSafeInteger(meta.size) || meta.size <= 0 || meta.size > cap) {
    return fail(413, "WF_OBJECT_SIZE_OVER_LIMIT");
  }
  const headers = objectHeaders(meta);
  if (request.method === "HEAD") {
    headers["Content-Length"] = String(meta.size);
    return new Response(null, { status: 200, headers });
  }
  if (request.method !== "GET") return fail(405, "WF_METHOD_NOT_ALLOWED");
  const hasRange = url.searchParams.has("offset") || url.searchParams.has("length");
  if (kind === "metadata") {
    if (hasRange) return fail(400, "WF_METADATA_RANGE_FORBIDDEN");
    const item = await env.WF_R2.get(key);
    if (!item?.body || item.size !== meta.size || item.httpEtag !== meta.httpEtag) {
      return fail(502, "WF_R2_METADATA_CHANGED");
    }
    headers["Content-Length"] = String(item.size);
    return new Response(item.body, { status: 200, headers });
  }
  if (!url.searchParams.has("offset") || !url.searchParams.has("length")) {
    return fail(400, "WF_BLOB_REQUIRES_BOUNDED_RANGE");
  }
  const offset = sizeInt(url.searchParams.get("offset"));
  const length = sizeInt(url.searchParams.get("length"));
  if (offset === null || length === null || length < 1 || length > CHUNK_MAX ||
      offset >= meta.size || offset + length > meta.size) {
    return fail(416, "WF_BLOB_RANGE_INVALID");
  }
  const item = await env.WF_R2.get(key, { range: { offset, length } });
  if (!item?.body || item.size !== meta.size || item.httpEtag !== meta.httpEtag ||
      !item.range || item.range.offset !== offset || item.range.length !== length) {
    return fail(502, "WF_R2_RANGE_INCONSISTENT");
  }
  headers["Content-Length"] = String(length);
  headers["Content-Range"] = "bytes " + offset + "-" + (offset + length - 1) + "/" + meta.size;
  return new Response(item.body, { status: 206, headers });
}
async function inventory(url, env) {
  const p = [...url.searchParams.keys()];
  if (p.some(k => k !== "cursor") || p.length > 1) return fail(400, "WF_CURSOR_INVALID");
  let cursor = url.searchParams.get("cursor") || undefined;
  if (cursor && (cursor.length > 2048 || /[\u0000-\u001f]/.test(cursor))) {
    return fail(400, "WF_CURSOR_INVALID");
  }
  const t = performance.now();
  let pageCount = 0, count = 0, bytes = 0, truncated = false;
  for (let i = 0; i < INVENTORY_PAGES; i++) {
    const result = await env.WF_R2.list({ prefix: PREFIX, limit: 1000, ...(cursor ? { cursor } : {}) });
    pageCount++;
    count += result.objects.length;
    for (const obj of result.objects) bytes += obj.size;
    truncated = !!result.truncated;
    if (!truncated) { cursor = undefined; break; }
    if (!result.cursor || result.cursor === cursor) return fail(502, "WF_R2_CURSOR_STALLED");
    cursor = result.cursor;
  }
  return json({
    ok: true, read_only: true, scope: PREFIX, complete: !truncated,
    next_cursor: truncated ? cursor : null, pages_scanned: pageCount,
    objects_scanned: count, total_bytes: bytes,
    query_ms: Math.round(performance.now() - t),
  });
}
export default {
  async fetch(request, env) {
    try {
      if (!env.WF_API_TOKEN || typeof env.WF_API_TOKEN !== "string") {
        return fail(503, "WF_SECRET_NOT_CONFIGURED");
      }
      if (!(await authorized(request, env.WF_API_TOKEN))) {
        return fail(401, "WF_UNAUTHORIZED");
      }
      if (!env.WF_R2) return fail(503, "WF_R2_BINDING_MISSING");
      const url = new URL(request.url);
      if (url.pathname === "/r2/object") {
        return await getObject(request, env, url);
      }
      if (url.pathname === "/r2/private-reading/list") {
        if (request.method !== "GET") return fail(405, "WF_METHOD_NOT_ALLOWED");
        return await privateList(env, url);
      }
      if (url.pathname === "/r2/private-reading/object") {
        return await getObject(request, env, url, true);
      }
      if (request.method !== "GET") return fail(405, "WF_METHOD_NOT_ALLOWED");
      if (url.pathname === "/health") {
        return json({ ok: true, r2_binding_present: true, read_only: true });
      }
      if (url.pathname === "/r2/status") {
        const start = performance.now();
        const found = await env.WF_R2.list({ prefix: PREFIX, limit: 1 });
        return json({
          ok: true, r2_connected: true, read_only: true,
          metadata_objects_returned: found.objects.length,
          query_ms: Math.round(performance.now() - start),
        });
      }
      if (url.pathname === "/r2/inventory") {
        return await inventory(url, env);
      }
      return fail(404, "WF_ROUTE_UNKNOWN");
    } catch {
      // Never send caller request, private object key or stack trace into logs.
      return fail(502, "WF_R2_READ_FAILED");
    }
  },
};
