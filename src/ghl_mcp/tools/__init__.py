"""Import all tool surface modules.

Importing this package triggers all ``@mcp.tool(...)`` decorators,
registering every tool with the shared FastMCP instance in ``_mcp.py``.

Surfaces (92 tools total):
  calendars               7
  calendar_groups         6
  users                   2
  tags                    5
  workflows               3
  contacts                2
  conversations           4
  opportunities           4
  invoices               11
  invoice_templates       6
  products               12   (products 5 + prices 5 + inventory 2)
  orders                  2
  subscriptions           2
  transactions            1
  admin_payments          2
  email_campaigns         8
  custom_fields           7
  funnels_forms_surveys   8   (funnels 3 + forms 3 + surveys 2)
"""

from ghl_mcp.tools import (  # noqa: F401
    admin_payments,
    calendar_groups,
    calendars,
    contacts,
    conversations,
    custom_fields,
    email_campaigns,
    funnels_forms_surveys,
    invoice_templates,
    invoices,
    opportunities,
    orders,
    products,
    subscriptions,
    tags,
    transactions,
    users,
    workflows,
)
