# fal.ai adapter

Use the configured first-party fal MCP connection and its actual available tools.
In tkstack it is named `fal` and uses `https://mcp.fal.ai/mcp-relay` with host OAuth.
Another harness may expose different tool names. Discover catalog/schema/pricing
through those tools; never invent an endpoint or tool signature.

Use the exact requested provider/model and inspect the current input schema.
Upload only authorized inputs. Submit bounded work with the actual synchronous
or async job API; preserve the endpoint and request IDs through status/result
retrieval. Setup/discovery alone does not authorize generation.

Report authentication or missing tools accurately. A copied skill supplies no
runtime credentials. Do not switch accounts, providers, or models to get around
a failure. For explicit Higgsfield requests, use its real installed adapter if
available; provider-neutral production guidance does not convert fal into it.
