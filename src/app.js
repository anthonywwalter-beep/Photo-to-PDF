import express from "express";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));

export function createApp() {
  const app = express();
  app.disable("x-powered-by");
  // Uploaded files are never written to disk and request bodies are never logged.
  app.get("/health", (_req, res) => res.json({ ok: true }));
  app.use(express.static(path.join(here, "..", "public")));
  return app;
}
