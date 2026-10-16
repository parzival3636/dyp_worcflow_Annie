// Supabase Edge Function — GitHub Webhook Receiver
// Deployed at: https://<your-project>.supabase.co/functions/v1/github-webhook
// This function receives GitHub push events, verifies the signature,
// and inserts the raw payload into the webhook_events table.

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_KEY = Deno.env.get("SERVICE_KEY")!;  // CLI blocks SUPABASE_ prefix; use SERVICE_KEY
const WEBHOOK_SECRET = Deno.env.get("GITHUB_WEBHOOK_SECRET")!;

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);

async function verifySignature(body: string, signature: string | null): Promise<boolean> {
  if (!signature || !signature.startsWith("sha256=")) return false;

  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(WEBHOOK_SECRET),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );

  const sig = await crypto.subtle.sign("HMAC", key, encoder.encode(body));
  const expected = "sha256=" + Array.from(new Uint8Array(sig))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");

  return expected === signature;
}

serve(async (req: Request) => {
  if (req.method !== "POST") {
    return new Response("Method not allowed", { status: 405 });
  }

  const body = await req.text();
  const signature = req.headers.get("x-hub-signature-256");
  const event = req.headers.get("x-github-event");

  // Verify webhook signature
  const valid = await verifySignature(body, signature);
  if (!valid) {
    console.error("Invalid webhook signature");
    return new Response("Unauthorized", { status: 401 });
  }

  // Only handle push events
  if (event !== "push") {
    return new Response(JSON.stringify({ message: "Event ignored" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }

  const payload = JSON.parse(body);
  const commits = payload.commits || [];

  if (commits.length === 0) {
    return new Response(JSON.stringify({ message: "No commits in push" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }

  // Insert each commit as a separate webhook event
  const events = commits.map((commit: any) => ({
    repo_name: payload.repository?.name,
    commit_sha: commit.id,
    commit_message: commit.message,
    author: commit.author?.username || commit.author?.name || "unknown",
    diff_url: commit.url,
    raw_payload: payload,
    status: "pending",
  }));

  const { error } = await supabase.from("webhook_events").insert(events);

  if (error) {
    console.error("Supabase insert error:", error);
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }

  console.log(`Inserted ${events.length} webhook event(s) from ${payload.repository?.full_name}`);

  return new Response(
    JSON.stringify({ received: events.length, status: "queued" }),
    { status: 200, headers: { "Content-Type": "application/json" } }
  );
});
