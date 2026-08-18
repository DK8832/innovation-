import { spawn } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { createServer } from "node:http";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { registerAppResource, RESOURCE_MIME_TYPE } from "@modelcontextprotocol/ext-apps/server";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { z } from "zod/v3";

const MODULE_DIR = dirname(fileURLToPath(import.meta.url));
const PLUGIN_ROOT = existsSync(join(MODULE_DIR, ".codex-plugin")) ? MODULE_DIR : dirname(MODULE_DIR);
const TEMPLATE_URI = "ui://factlens/workbench-v1.html";
const widgetHtml = readFileSync(join(PLUGIN_ROOT, "ui", "workbench.html"), "utf8");
const configuredMaxConcurrency = Number(process.env.FACTLENS_MAX_CONCURRENCY || 4);
const maxConcurrentAnalyses = Number.isFinite(configuredMaxConcurrency)
  ? Math.max(1, Math.floor(configuredMaxConcurrency))
  : 4;
let activeAnalyses = 0;

function createFactLensServer() {
  const server = new McpServer(
    { name: "factlens", version: "0.1.0" },
    { capabilities: { tools: {}, resources: {} } },
  );

registerAppResource(
  server,
  "factlens-workbench",
  TEMPLATE_URI,
  {},
  async () => ({
    contents: [
      {
        uri: TEMPLATE_URI,
        mimeType: RESOURCE_MIME_TYPE,
        text: widgetHtml,
        _meta: {
          ui: {
            prefersBorder: true,
            csp: {
              connectDomains: [],
              resourceDomains: [],
            },
          },
        },
      },
    ],
  }),
);

const toolUiMeta = {
  ui: { resourceUri: TEMPLATE_URI },
  "openai/outputTemplate": TEMPLATE_URI,
};

server.registerTool(
  "open_factlens",
  {
    title: "FactLens 검사기 열기",
    description:
      "Use this when 사용자가 FactLens 작업창을 직접 열어 답변과 기준 문서를 입력하려고 합니다. 자동 답변 검증에는 verify_answer를 사용하세요.",
    inputSchema: {},
    outputSchema: {
      view: z.literal("form"),
      pipeline_version: z.string(),
    },
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
      openWorldHint: false,
      idempotentHint: true,
    },
    _meta: {
      ...toolUiMeta,
      "openai/toolInvocation/invoking": "FactLens를 여는 중…",
      "openai/toolInvocation/invoked": "FactLens를 열었습니다.",
    },
  },
  async () => ({
    structuredContent: { view: "form", pipeline_version: "0.1.0" },
    content: [
      {
        type: "text",
        text: "FactLens 검사 작업창을 열었습니다. AI 답변과 기준 문서를 입력해 검사할 수 있습니다.",
      },
    ],
  }),
);

const referenceSchema = z.object({
  title: z.string().max(300).default("기준 문서"),
  text: z.string().min(1).max(200_000),
  url: z.string().max(2_000).optional(),
  published_at: z.string().max(100).optional(),
});

server.registerTool(
  "verify_answer",
  {
    title: "AI 답변 검증",
    description:
      "Use this when 사실 답변의 초안과 독립적인 기준 자료가 준비되어 있고, 최종 답변 전에 주장별 지지·모순·근거 부족·검증 불가를 확인해야 합니다. 검색 기능은 없으므로 답변 자체가 아닌 외부 근거를 reference_texts로 제공해야 합니다.",
    inputSchema: {
      answer: z.string().min(1).max(50_000).describe("검증할 AI 답변"),
      reference_texts: z
        .array(referenceSchema)
        .min(1)
        .max(20)
        .describe("비교 기준 문서 목록"),
      question: z.string().max(10_000).optional().describe("답변을 생성하게 한 원래 질문"),
      as_of: z.string().max(30).optional().describe("검사 기준일(YYYY-MM-DD)"),
    },
    outputSchema: {
      view: z.literal("result"),
      result: z.record(z.unknown()),
    },
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
      openWorldHint: false,
      idempotentHint: true,
    },
    _meta: {
      ...toolUiMeta,
      "openai/toolInvocation/invoking": "답변을 검증하는 중…",
      "openai/toolInvocation/invoked": "검증을 마쳤습니다.",
    },
  },
  async ({ answer, reference_texts, question = "", as_of }) => {
    const payload = {
      question,
      answer,
      mode: "document",
      reference_texts,
      ...(as_of ? { as_of } : {}),
    };
    const result = await analyze(payload);
    return {
      structuredContent: { view: "result", result },
      content: [{ type: "text", text: modelSummary(result) }],
    };
  },
);

  return server;
}

function analyze(payload) {
  if (activeAnalyses >= maxConcurrentAnalyses) {
    return Promise.reject(new Error("FactLens가 처리 중입니다. 잠시 후 다시 시도해 주세요."));
  }
  activeAnalyses += 1;
  return runAnalysis(payload).finally(() => {
    activeAnalyses -= 1;
  });
}

function runAnalysis(payload) {
  const python = process.env.FACTLENS_PYTHON || "python";
  const script = join(PLUGIN_ROOT, "scripts", "analyze.py");

  return new Promise((resolve, reject) => {
    const child = spawn(python, [script], {
      cwd: PLUGIN_ROOT,
      env: {
        ...process.env,
        PYTHONUTF8: "1",
        PYTHONIOENCODING: "utf-8",
        PYTHONDONTWRITEBYTECODE: "1",
      },
      windowsHide: true,
      stdio: ["pipe", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    let settled = false;

    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      child.kill();
      reject(new Error("FactLens 분석 시간이 30초를 초과했습니다."));
    }, 30_000);

    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (chunk) => { stdout += chunk; });
    child.stderr.on("data", (chunk) => { stderr += chunk; });
    child.on("error", (error) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      reject(new Error(`Python 실행 실패: ${error.message}`));
    });
    child.on("close", (code) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      let parsed;
      try {
        parsed = JSON.parse(stdout || "{}");
      } catch {
        reject(new Error(`FactLens 결과를 읽지 못했습니다. ${stderr.trim()}`.trim()));
        return;
      }
      if (code !== 0 || parsed.error) {
        reject(new Error(parsed.error || stderr.trim() || `FactLens가 코드 ${code}로 종료되었습니다.`));
        return;
      }
      resolve(parsed);
    });

    child.stdin.end(JSON.stringify(payload));
  });
}

function modelSummary(result) {
  const s = result.summary;
  const percentage = (value) => value == null ? "계산 불가" : `${Math.round(value * 100)}%`;
  const lines = [
    `FactLens가 ${s.total_claims}개 주장을 검사했습니다.`,
    `지지 ${s.supported}개, 모순 ${s.contradicted}개, 근거 부족 ${s.insufficient}개, 검증 불가 ${s.unverifiable}개입니다.`,
    `지원율 ${percentage(s.support_rate)}, 모순율 ${percentage(s.contradiction_rate)}, 초기 위험도 ${percentage(s.risk)}입니다.`,
  ];
  for (const item of result.claims) {
    lines.push(`- [${item.label}] ${item.claim.exact_quote}: ${item.rationale}`);
  }
  lines.push("주의: 이 결과는 제공된 문서와의 일치성 검사이며 독립적인 진실 판정을 보장하지 않습니다.");
  return lines.join("\n");
}

async function startStdio() {
  const server = createFactLensServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

async function startHttp() {
  const port = Number(process.env.PORT || 3000);
  const host = process.env.HOST || "0.0.0.0";
  const httpServer = createServer(async (req, res) => {
    const url = new URL(req.url || "/", `http://${req.headers.host || "localhost"}`);

    if (req.method === "GET" && url.pathname === "/health") {
      sendJson(res, 200, { status: "ok", service: "factlens", version: "0.1.0" });
      return;
    }

    if (req.method === "GET" && url.pathname === "/.well-known/openai-apps-challenge") {
      const token = process.env.OPENAI_APPS_CHALLENGE;
      if (!token) {
        res.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
        res.end("Challenge token is not configured.");
        return;
      }
      res.writeHead(200, { "content-type": "text/plain; charset=utf-8" });
      res.end(token);
      return;
    }

    if (req.method !== "POST" || url.pathname !== "/mcp") {
      sendJson(res, 405, {
        jsonrpc: "2.0",
        error: { code: -32000, message: "Method not allowed." },
        id: null,
      });
      return;
    }

    try {
      const body = await readJsonBody(req, 5_000_000);
      const server = createFactLensServer();
      const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined });
      await server.connect(transport);
      await transport.handleRequest(req, res, body);
      res.on("close", () => {
        void transport.close();
        void server.close();
      });
    } catch (error) {
      console.error("FactLens MCP request failed:", error);
      if (!res.headersSent) {
        const status = error instanceof SyntaxError ? 400
          : error.message === "Request body is too large." ? 413
            : 500;
        sendJson(res, status, {
          jsonrpc: "2.0",
          error: {
            code: status === 500 ? -32603 : -32600,
            message: status === 400 ? "Invalid JSON request."
              : status === 413 ? "Request body is too large."
                : "Internal server error",
          },
          id: null,
        });
      }
    }
  });

  httpServer.listen(port, host, () => {
    console.log(`FactLens MCP server listening on http://${host}:${port}/mcp`);
  });
}

function sendJson(res, status, value) {
  res.writeHead(status, { "content-type": "application/json; charset=utf-8" });
  res.end(JSON.stringify(value));
}

async function readJsonBody(req, maxBytes) {
  const chunks = [];
  let total = 0;
  for await (const chunk of req) {
    total += chunk.length;
    if (total > maxBytes) throw new Error("Request body is too large.");
    chunks.push(chunk);
  }
  return JSON.parse(Buffer.concat(chunks).toString("utf8"));
}

if (process.env.FACTLENS_TRANSPORT === "http") {
  await startHttp();
} else {
  await startStdio();
}
