import assert from "node:assert/strict";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const sourceRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const pluginRoot = process.env.FACTLENS_PLUGIN_ROOT || sourceRoot;
const transport = new StdioClientTransport({
  command: "cmd.exe",
  args: ["/d", "/s", "/c", "call", join(pluginRoot, "scripts", "launch_mcp.cmd")],
  cwd: pluginRoot,
  stderr: "pipe",
});
const client = new Client({ name: "factlens-smoke-test", version: "0.1.0" });

try {
  await client.connect(transport);

  const listed = await client.listTools();
  const names = listed.tools.map((tool) => tool.name);
  assert.deepEqual(names.sort(), ["open_factlens", "verify_answer"]);
  const verifyTool = listed.tools.find((tool) => tool.name === "verify_answer");
  assert.match(verifyTool.description, /^Use this when/);
  assert.equal(verifyTool.annotations.readOnlyHint, true);
  assert.equal(verifyTool.annotations.idempotentHint, true);
  assert.ok(verifyTool.outputSchema);

  const opened = await client.callTool({ name: "open_factlens", arguments: {} });
  assert.equal(opened.structuredContent.view, "form");

  const resource = await client.readResource({ uri: "ui://factlens/workbench-v1.html" });
  assert.match(resource.contents[0].mimeType, /text\/html/);
  assert.match(resource.contents[0].text, /FactLens/);

  const checked = await client.callTool({
    name: "verify_answer",
    arguments: {
      question: "세종대왕은 언제 태어났나?",
      answer: "세종대왕은 1398년에 태어났다.",
      reference_texts: [
        { title: "기준 문서", text: "세종대왕은 1397년 5월 15일에 태어났다." },
      ],
      as_of: "2026-08-18",
    },
  });
  assert.ok(checked.structuredContent, JSON.stringify(checked));
  assert.equal(checked.structuredContent.view, "result");
  assert.equal(checked.structuredContent.result.summary.contradicted, 1);
  assert.equal(checked.structuredContent.result.claims[0].label, "CONTRADICTED");

  process.stdout.write("FactLens MCP smoke test passed.\n");
} finally {
  await client.close();
}
