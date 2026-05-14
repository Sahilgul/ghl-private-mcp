# ghl-private-mcp

Standalone [MCP](https://modelcontextprotocol.io) server exposing **92 GoHighLevel tools** via the Private Integration Token (PIT) API.

Fills the gaps in the official LeadConnector MCP — invoices, products, email campaigns, custom fields, opportunities, conversations, and more.

## Tools

20 surfaces · 92 tools — all namespaced as `ghl.private.<surface>.<action>`:

`calendars` · `calendar_groups` · `users` · `tags` · `workflows` · `contacts` · `conversations` · `opportunities` · `invoices` · `invoice_templates` · `products` · `orders` · `subscriptions` · `transactions` · `payments` · `email_campaigns` · `custom_fields` · `funnels` · `forms` · `surveys`

## Setup

```bash
# 1. Clone and install
pip install -e .

# 2. Add credentials
echo "GHL_PIT_TOKEN=pit-..." >> .env
echo "GHL_LOCATION_ID=loc-..." >> .env

# 3. Run
python -m ghl_mcp.server --transport http --host 0.0.0.0 --port 8000
```

## Connect

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({
    "ghl": {"url": "http://localhost:8000/mcp", "transport": "streamable_http"}
})
tools = await client.get_tools()  # returns all 92 tools
```

## Requirements

Python 3.11+ · `mcp[cli]` · `httpx` · `python-dotenv`
