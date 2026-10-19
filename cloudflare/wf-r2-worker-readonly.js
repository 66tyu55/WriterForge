/**
 * WriterForge R2 read-only Worker, V67.
 * Deploy manually to the EXISTING wf-r2-api Worker; keep existing WF_R2 R2
 * binding and WF_API_TOKEN secret. No R2 writes, no raw bucket traversal.
 *
 * V69 adds strictly scoped read-only private-reading list and ranged content.
 * V72 adds content-addressed, separately authenticated index-only writes.
 * Existing /r2/object, /health,
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
const INDEX_ROOT = PREFIX + "indexes/v1/";
const INDEX_MAX_PART = 1024 * 1024;  // Each upload <=1MiB.
const INDEX_MANIFEST_CAP = 64 * 1024;
const INDEX_MAX_PARTS = 256;       // <=256MiB indexed book.
const INDEX_REF_LIST_PAGE = 32;



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


function indexPath(key) {
  if (typeof key !== "string" || key.length > 210 || !key.startsWith(INDEX_ROOT)) {
    return null;
  }
  const suffix = key.slice(INDEX_ROOT.length);
  let matched = /^chunks\/([0-9a-f]{64})\.bin$/.exec(suffix);
  if (matched) return {kind:"blob", sha:matched[1], cap:INDEX_MAX_PART};
  matched = /^refs\/([0-9a-f]{64})\/([0-9a-f]{64})\.json$/.exec(suffix);
  if (matched) return {
    kind:"metadata", source_key_sha:matched[1],
    sha:matched[2], cap:INDEX_MANIFEST_CAP,
  };
  return null;
}
function hexOf(buffer) {
  return Array.from(new Uint8Array(buffer)).map(
    v => v.toString(16).padStart(2,"0")).join("");
}
function isHexSHA(s) {
  return typeof s === "string" && SHA.test(s);
}
function safeManifest(doc, entry) {
  if (entry.kind !== "metadata" || !doc || typeof doc !== "object" ||
      Array.isArray(doc)) return false;
  const allowed = new Set([
    "format","source_key_sha256","source_sha256","source_size",
    "source_etag","book_id","parser_version","index_sha256","index_bytes",
    "chunks","units","chapters","encoding","provisional_legacy",
    "literary_verified","category",
  ]);
  if (Object.keys(doc).some(k => !allowed.has(k))) return false;
  if (doc.format !== "writerforge.r2.index.v1" ||
      doc.source_key_sha256 !== entry.source_key_sha ||
      !isHexSHA(doc.source_sha256) ||
      !isHexSHA(doc.index_sha256) ||
      doc.book_id !== "b_" + doc.source_sha256.slice(0,32) ||
      doc.parser_version !== "v68.lexical.v1" ||
      !Number.isSafeInteger(doc.source_size) || doc.source_size < 1 ||
      doc.source_size > BLOB_MAX ||
      typeof doc.source_etag !== "string" || doc.source_etag.length < 2 ||
      doc.source_etag.length > 200 ||
      !Number.isSafeInteger(doc.index_bytes) || doc.index_bytes < 1 ||
      doc.index_bytes > BLOB_MAX ||
      !Number.isSafeInteger(doc.units) || doc.units < 1 ||
      !Number.isSafeInteger(doc.chapters) || doc.chapters < 0 ||
      !["utf-8","utf-8-sig","utf-16","gb18030"].includes(doc.encoding) ||
      typeof doc.provisional_legacy !== "boolean" ||
      doc.literary_verified !== false ||
      !["仙侠","科幻","历史","待分类","玄幻","古典","武侠",
         "都市","悬疑","灵异","言情","游戏","军事","竞技",
         "体育","轻小说","奇幻"].includes(doc.category) ||
      !Array.isArray(doc.chunks) ||
      doc.chunks.length < 1 || doc.chunks.length > INDEX_MAX_PARTS) return false;
  let size = 0;
  for (const part of doc.chunks) {
    if (!part || typeof part !== "object" || Array.isArray(part) ||
        Object.keys(part).some(k => k !== "sha256" && k !== "size") ||
        !isHexSHA(part.sha256) ||
        !Number.isSafeInteger(part.size) ||
        part.size < 1 || part.size > INDEX_MAX_PART) return false;
    size += part.size;
  }
  return size === doc.index_bytes;
}
async function indexPut(request, env, url) {
  if (request.method !== "PUT") return fail(405,"WF_INDEX_WRITE_METHOD_DENIED");
  const items = [...url.searchParams.entries()];
  if (items.length !== 1 || items[0][0] !== "key") {
    return fail(400,"WF_INDEX_WRITE_KEY_REQUIRED");
  }
  const key = items[0][1];
  const item = indexPath(key);
  if (!item) return fail(403,"WF_INDEX_WRITE_SCOPE_FORBIDDEN");
  const headerLen = sizeInt(request.headers.get("Content-Length"));
  if (headerLen === null || headerLen < 1 || headerLen > item.cap) {
    return fail(413,"WF_INDEX_WRITE_BUDGET_EXCEEDED");
  }
  // Small bounded chunk, one WebCrypto digest. Never read a full novel.
  const raw = await request.arrayBuffer();
  if (raw.byteLength !== headerLen) return fail(400,"WF_INDEX_WRITE_LENGTH_MISMATCH");
  const digest = hexOf(await crypto.subtle.digest("SHA-256",raw));
  if (digest !== item.sha) return fail(422,"WF_INDEX_WRITE_SHA_MISMATCH");
  if (item.kind === "metadata") {
    let doc;
    try { doc = JSON.parse(new TextDecoder("utf-8",{fatal:true}).decode(raw)); }
    catch { return fail(400,"WF_INDEX_MANIFEST_NOT_JSON"); }
    if (!safeManifest(doc,item)) return fail(400,"WF_INDEX_MANIFEST_INVALID");
    // Never advertise an index if any referenced chunk is missing/wrong.
    for (const part of doc.chunks) {
      const chunkKey = INDEX_ROOT + "chunks/" + part.sha256 + ".bin";
      const object = await env.WF_R2.head(chunkKey);
      if (!object || object.size !== part.size ||
          object.customMetadata?.sha256 !== part.sha256) {
        return fail(409,"WF_INDEX_CHUNK_NOT_VERIFIED");
      }
    }
  }
  const old = await env.WF_R2.head(key);
  if (old) {
    if (old.size === headerLen && old.customMetadata?.sha256 === item.sha) {
      return json({ok:true,sha256:item.sha,size:headerLen,
                   created:false,immutable:true});
    }
    return fail(409,"WF_INDEX_IMMUTABLE_COLLISION");
  }
  // Atomic create-only: concurrent retry cannot replace a published object.
  const saved = await env.WF_R2.put(key,raw,{
    onlyIf:new Headers({"If-None-Match":"*"}),
    customMetadata:{sha256:item.sha,role:item.kind},
    httpMetadata:{contentType:"application/octet-stream"},
    sha256:raw instanceof ArrayBuffer ?
      await crypto.subtle.digest("SHA-256",raw) : undefined,
  });
  if (!saved) {
    const raced = await env.WF_R2.head(key);
    if (raced && raced.size === headerLen &&
        raced.customMetadata?.sha256 === item.sha) {
      return json({ok:true,sha256:item.sha,size:headerLen,
                   created:false,immutable:true});
    }
    return fail(409,"WF_INDEX_CONCURRENT_WRITE_FAILED");
  }
  if (saved.size !== headerLen ||
      saved.customMetadata?.sha256 !== item.sha) {
    return fail(502,"WF_INDEX_WRITE_READBACK_METADATA_FAILED");
  }
  return json({ok:true,sha256:item.sha,size:headerLen,
               created:true,immutable:true});
}
async function indexListRefs(env,url) {
  const params = [...url.searchParams.entries()];
  if (params.length < 1 || params.length > 2 ||
      new Set(params.map(x=>x[0])).size !== params.length ||
      params.some(p=>!["source_key_sha","cursor"].includes(p[0]))) {
    return fail(400,"WF_INDEX_LIST_PARAMS_INVALID");
  }
  const sourceKeyHash = url.searchParams.get("source_key_sha");
  if (!isHexSHA(sourceKeyHash)) return fail(400,"WF_INDEX_SOURCE_KEY_SHA_INVALID");
  const cursor = url.searchParams.get("cursor");
  if (cursor !== null && (!cursor || cursor.length > 2048 ||
      /[\u0000-\u001f]/.test(cursor))) return fail(400,"WF_INDEX_CURSOR_INVALID");
  const prefix = INDEX_ROOT+"refs/"+sourceKeyHash+"/";
  const data = await env.WF_R2.list({
    prefix,limit:INDEX_REF_LIST_PAGE,
    ...(cursor ? {cursor}:{}),
  });
  if (data.objects.length > INDEX_REF_LIST_PAGE ||
      (data.truncated && (!data.cursor || data.cursor === cursor))) {
    return fail(502,"WF_INDEX_LIST_INVALID_CURSOR");
  }
  const refs = [];
  for (const obj of data.objects) {
    const ref = indexPath(obj.key);
    if (!ref || ref.kind !== "metadata" ||
        ref.source_key_sha !== sourceKeyHash ||
        !Number.isSafeInteger(obj.size) || obj.size > INDEX_MANIFEST_CAP) {
      return fail(502,"WF_INDEX_LIST_OUTSIDE_SCOPE");
    }
    refs.push({manifest_sha256:ref.sha,size:obj.size});
  }
  return json({
    ok:true,read_only:true,
    format:"writerforge.index-ref-list.v1",
    source_key_sha256:sourceKeyHash,
    manifests:refs,
    complete:!data.truncated,
    next_cursor:data.truncated ? data.cursor : null,
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
async function getObject(request, env, url, privateMode = false, indexMode = false) {
  // Only the pinned single study library; no arbitrary paths or listing.
  const params = [...url.searchParams.keys()];
  if (params.length > 3 || params.some(k => !["key", "offset", "length"].includes(k)) ||
      new Set(params).size !== params.length) {
    return fail(400, "WF_OBJECT_QUERY_INVALID");
  }
  const key = url.searchParams.get("key");
  const indexItem = indexMode ? indexPath(key) : null;
  const kind = indexMode ? indexItem?.kind :
    (privateMode ? allowedPrivateKey(key) : allowedKey(key));
  if (!kind) return fail(403, "WF_OBJECT_OUTSIDE_PINNED_LIBRARY");
  const meta = await env.WF_R2.head(key);
  if (!meta) return fail(404, "WF_OBJECT_NOT_FOUND");
  if (indexMode && meta.customMetadata?.sha256 !== indexItem.sha) {
    return fail(502,"WF_INDEX_READ_METADATA_SHA_MISMATCH");
  }
  const cap = indexMode ? indexItem.cap :
    (kind === "blob" ? BLOB_MAX : SMALL_MAX);
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
      if (!env.WF_R2) return fail(503, "WF_R2_BINDING_MISSING");
      const url = new URL(request.url);
      if (url.pathname === "/r2/index/write") {
        if (!env.WF_INDEX_UPLOAD_TOKEN ||
            env.WF_INDEX_UPLOAD_TOKEN === env.WF_API_TOKEN) {
          return fail(503,"WF_INDEX_WRITER_SECRET_MISSING_OR_REUSED");
        }
        if (!(await authorized(request,env.WF_INDEX_UPLOAD_TOKEN))) {
          return fail(401,"WF_INDEX_WRITER_UNAUTHORIZED");
        }
        return await indexPut(request,env,url);
      }
      if (!(await authorized(request, env.WF_API_TOKEN))) {
        return fail(401, "WF_UNAUTHORIZED");
      }
      if (url.pathname === "/r2/index/object") {
        return await getObject(request,env,url,false,true);
      }
      if (url.pathname === "/r2/index/refs") {
        if (request.method !== "GET") return fail(405,"WF_INDEX_READ_METHOD");
        return await indexListRefs(env,url);
      }
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
