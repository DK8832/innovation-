import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";

const sourceRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const pluginRoot = process.env.FACTLENS_PLUGIN_ROOT || sourceRoot;
const port = 32147;
const child = spawn(process.execPath, [join(pluginRoot, "dist", "server.mjs")], {
  cwd: pluginRoot,
  env: {
    ...process.env,
    FACTLENS_TRANSPORT: "http",
    FACTLENS_PROJECT_ROOT: join(pluginRoot, "missing-project"),
    HOST: "127.0.0.1",
    OPENAI_APPS_CHALLENGE: "factlens-smoke-token",
    PORT: String(port),
  },
  windowsHide: true,
  stdio: ["ignore", "pipe", "pipe"],
});

let serverErrors = "";
child.stderr.setEncoding("utf8");
child.stderr.on("data", (chunk) => { serverErrors += chunk; });

const client = new Client({ name: "factlens-http-smoke-test", version: "0.1.0" });

try {
  const healthUrl = `http://127.0.0.1:${port}/health`;
  let healthy = false;
  for (let attempt = 0; attempt < 40; attempt += 1) {
    try {
      const response = await fetch(healthUrl);
      healthy = response.ok;
      if (healthy) break;
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
  }
  assert.equal(healthy, true, serverErrors || "HTTP health check failed");

  const challenge = await fetch(
    `http://127.0.0.1:${port}/.well-known/openai-apps-challenge`,
  );
  assert.equal(challenge.status, 200);
  assert.equal(await challenge.text(), "factlens-smoke-token");

  const invalidJson = await fetch(`http://127.0.0.1:${port}/mcp`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: "{",
  });
  assert.equal(invalidJson.status, 400);

  const transport = new StreamableHTTPClientTransport(
    new URL(`http://127.0.0.1:${port}/mcp`),
  );
  await client.connect(transport);

  const listed = await client.listTools();
  assert.deepEqual(listed.tools.map((tool) => tool.name).sort(), ["open_factlens", "verify_answer"]);

  const checked = await client.callTool({
    name: "verify_answer",
    arguments: {
      answer: "세종대왕은 1398년에 태어났다.",
      reference_texts: [
        { title: "기준 문서", text: "세종대왕은 1397년 5월 15일에 태어났다." },
      ],
    },
  });
  assert.equal(checked.structuredContent.result.summary.contradicted, 1);
  process.stdout.write("FactLens HTTP MCP smoke test passed.\n");
} finally {
  await client.close().catch(() => {});
  child.kill();
}
