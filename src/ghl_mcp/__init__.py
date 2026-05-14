"""ghl_mcp — standalone GoHighLevel PIT MCP server (92 tools).

Surfaces
--------
  calendars, calendar_groups, users, tags, workflows, contacts,
  conversations, opportunities, invoices, invoice_templates, products,
  orders, subscriptions, transactions, admin_payments,
  email_campaigns, custom_fields, funnels, forms, surveys

Start the server
----------------
  # HTTP (network-accessible):
  python -m ghl_mcp.server --transport http --port 8000

  # stdio (spawned by MCP client):
  python -m ghl_mcp.server
"""
