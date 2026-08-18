# FactLens public submission checklist

The plugin code is ready to run as a stateless HTTP MCP server. Public directory submission still requires publisher-owned infrastructure and policy pages.

## Deploy

1. Build the container from this directory.
2. Publish it behind a stable HTTPS origin.
3. Set `OPENAI_APPS_CHALLENGE` to the token shown by the OpenAI submission portal when domain verification is requested.
4. Confirm `GET /health` and the production `/mcp` endpoint.
5. Keep submitted reference text only in process memory and do not add request-body logging.

## Submission materials still owned by the publisher

- Verified individual or business identity with Apps Management write access
- Production MCP URL ending in `/mcp`
- Product website URL
- Support URL
- Privacy policy URL describing answer and reference-text processing
- Terms URL
- Country or region availability
- Release notes

Import `chatgpt-app-submission.json` in the submission form, scan the deployed tools, resolve any portal findings, and submit for review only after the public URLs are final.
