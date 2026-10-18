// V67: paste this block INSIDE async fetch(request, env), just before
// the final: return reply({ error: "Not Found" }, 404);
// Keep the existing WF_API_TOKEN check and GET-only restriction ABOVE it.
// This route serves ONE pinned public-domain classic source from the private R2
// bucket. No arbitrary key input, public URL, listings, writes or deletions.

if (url.pathname === "/r2/source/laocanyouji") {
  if (!env.WF_R2) return reply({ error: "R2_NOT_BOUND" }, 503);

  const library = "laocanyouji-25124";
  const root = "writerforge/v1/libraries/" + library + "/";
  const snapshot = "7fe1ceff8d637139d51b0b6bf2de6a7de220aeaea670247868fa17cc55270dd2";
  const pinnedSource = "273f4cbaecb4c4d396ecec7103b4761e62bde0c0f368185a1697c1880cfe9cf7";
  const limit = 8 * 1024 * 1024;

  try {
    const manifestObj = await env.WF_R2.get(root + "snapshots/" + snapshot + ".json");
    if (!manifestObj || manifestObj.size > 131072) {
      return reply({ error: "PINNED_MANIFEST_MISSING" }, 404);
    }

    const manifestBytes = await manifestObj.arrayBuffer();
    const hash = await crypto.subtle.digest("SHA-256", manifestBytes);
    const computed = Array.from(new Uint8Array(hash))
      .map(x => x.toString(16).padStart(2, "0")).join("");
    if (computed !== snapshot) {
      return reply({ error: "MANIFEST_INTEGRITY_FAILED" }, 502);
    }

    const manifest = JSON.parse(new TextDecoder().decode(manifestBytes));
    const meta = manifest.files && manifest.files["source.txt"];
    if (
      manifest.format !== "writerforge.r2.xuehai.v1" ||
      manifest.library !== library ||
      !meta || meta.sha256 !== pinnedSource ||
      !Number.isSafeInteger(meta.size) || meta.size <= 0 ||
      meta.size > limit
    ) {
      return reply({ error: "PINNED_SOURCE_METADATA_INVALID" }, 502);
    }

    const original = await env.WF_R2.get(root + "blobs/" + pinnedSource);
    if (!original || original.size !== meta.size || !original.body) {
      return reply({ error: "PINNED_SOURCE_BLOB_MISSING" }, 502);
    }

    // Authenticated HTTPS response; WF verifies every byte's SHA256 again.
    return new Response(original.body, {
      status: 200,
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
        "X-WF-Library": library,
        "X-WF-Snapshot-SHA256": snapshot,
        "X-WF-Source-SHA256": pinnedSource,
        "X-WF-Source-Bytes": String(meta.size)
      }
    });
  } catch (error) {
    return reply({ error: "PINNED_SOURCE_READ_FAILED" }, 502);
  }
}
