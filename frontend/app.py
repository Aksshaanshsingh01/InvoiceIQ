from nicegui import events, run, ui

from frontend.api_client import (
    get_dashboard,
    get_invoices,
    get_invoice,
    search_invoices,
    search_clients,
    upload_invoice,
)

import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# HELPERS
# ============================================================

def format_currency(value):
    """Format a numeric value as Indian Rupees."""
    return f"₹{float(value or 0):,.2f}"


def header():
    """Create the common InvoiceIQ navigation header."""

    with ui.header().classes(
        "bg-blue-500 text-white items-center justify-between"
    ):
        ui.label("InvoiceIQ").classes(
            "text-2xl font-bold"
        )

        with ui.row().classes("gap-2"):
            ui.button(
                "DASHBOARD",
                on_click=lambda: ui.navigate.to("/"),
            ).props("flat color=white")

            ui.button(
                "INVOICES",
                on_click=lambda: ui.navigate.to("/invoices"),
            ).props("flat color=white")

            ui.button(
                "UPLOAD",
                on_click=lambda: ui.navigate.to("/upload"),
            ).props("flat color=white")


def show_error(container, message):
    """Display an error inside a UI container."""

    container.clear()

    with container:
        ui.label(message).classes(
            "text-red-600 text-lg"
        )


# ============================================================
# DASHBOARD
# ============================================================

@ui.page("/")
def dashboard_page():

    header()

    with ui.column().classes(
        "w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 gap-0"
    ):

        # --------------------------------------------------------
        # Page heading
        # --------------------------------------------------------

        with ui.row().classes(
            "w-full items-end justify-between gap-4 mb-8"
        ):
            with ui.column().classes("gap-1"):
                ui.label("Dashboard").classes(
                    "text-4xl font-bold tracking-tight"
                )
                ui.label(
                    "Financial overview and invoice activity"
                ).classes(
                    "text-base text-gray-500"
                )

            ui.button(
                "REFRESH",
                icon="refresh",
                on_click=lambda: ui.navigate.to("/"),
            ).props(
                "outline color=primary"
            ).classes(
                "rounded-lg"
            )

        try:
            data = get_dashboard()
        except Exception as error:
            with ui.card().classes(
                "w-full border border-red-200 bg-red-50 rounded-xl shadow-none p-6"
            ):
                ui.label(
                    "Unable to connect to InvoiceIQ API"
                ).classes(
                    "text-xl font-semibold text-red-700"
                )
                ui.label(str(error)).classes(
                    "text-sm text-red-600 mt-1"
                )
            return

        financial = data.get("financial", {})
        invoices = data.get("invoices", {})
        tax = data.get("tax", {})
        parties = data.get("parties", {})

        supplier_data = parties.get("suppliers", {})
        customer_data = parties.get("customers", {})

        suppliers = supplier_data.get("suppliers", [])
        customers = customer_data.get("customers", [])

        # --------------------------------------------------------
        # Financial KPI Cards
        # --------------------------------------------------------

        ui.label("Financial Overview").classes(
            "text-xl font-bold text-gray-800 mb-3"
        )

        with ui.grid(columns=4).classes(
            "w-full gap-4 mb-8"
        ):

            with ui.card().classes(
                "w-full rounded-xl border border-gray-200 shadow-sm p-5"
            ):
                with ui.row().classes(
                    "w-full items-center justify-between"
                ):
                    with ui.column().classes("gap-0"):
                        ui.label("TOTAL SALES").classes(
                            "text-xs font-bold tracking-wider text-gray-500"
                        )
                        ui.label(
                            format_currency(financial.get("total_sales"))
                        ).classes(
                            "text-2xl font-bold text-green-600 mt-2"
                        )
                    ui.icon("trending_up").classes(
                        "text-3xl text-green-600"
                    )

            with ui.card().classes(
                "w-full rounded-xl border border-gray-200 shadow-sm p-5"
            ):
                with ui.row().classes(
                    "w-full items-center justify-between"
                ):
                    with ui.column().classes("gap-0"):
                        ui.label("TOTAL PURCHASES").classes(
                            "text-xs font-bold tracking-wider text-gray-500"
                        )
                        ui.label(
                            format_currency(financial.get("total_purchases"))
                        ).classes(
                            "text-2xl font-bold text-blue-600 mt-2"
                        )
                    ui.icon("shopping_cart").classes(
                        "text-3xl text-blue-600"
                    )

            with ui.card().classes(
                "w-full rounded-xl border border-gray-200 shadow-sm p-5"
            ):
                with ui.row().classes(
                    "w-full items-center justify-between"
                ):
                    with ui.column().classes("gap-0"):
                        ui.label("TOTAL TAX").classes(
                            "text-xs font-bold tracking-wider text-gray-500"
                        )
                        ui.label(
                            format_currency(financial.get("total_tax"))
                        ).classes(
                            "text-2xl font-bold text-purple-600 mt-2"
                        )
                    ui.icon("receipt_long").classes(
                        "text-3xl text-purple-600"
                    )

            with ui.card().classes(
                "w-full rounded-xl border border-red-100 bg-red-50 shadow-sm p-5"
            ):
                with ui.row().classes(
                    "w-full items-center justify-between"
                ):
                    with ui.column().classes("gap-0"):
                        ui.label("OUTSTANDING PAYABLES").classes(
                            "text-xs font-bold tracking-wider text-red-600"
                        )
                        ui.label(
                            format_currency(
                                financial.get("outstanding_amount")
                            )
                        ).classes(
                            "text-2xl font-bold text-red-600 mt-2"
                        )
                    ui.icon("account_balance_wallet").classes(
                        "text-3xl text-red-600"
                    )

        # --------------------------------------------------------
        # Invoice Activity
        # --------------------------------------------------------

        ui.label("Invoice Activity").classes(
            "text-xl font-bold text-gray-800 mb-3"
        )

        with ui.grid(columns=4).classes(
            "w-full gap-4 mb-8"
        ):

            metrics = [
                (
                    "TOTAL INVOICES",
                    invoices.get("total_invoice_count", 0),
                    "description",
                    "text-gray-800",
                ),
                (
                    "SALES INVOICES",
                    invoices.get("sales_invoice_count", 0),
                    "arrow_upward",
                    "text-green-600",
                ),
                (
                    "PURCHASE INVOICES",
                    invoices.get("purchase_invoice_count", 0),
                    "shopping_bag",
                    "text-blue-600",
                ),
                (
                    "UNPAID PURCHASES",
                    invoices.get("unpaid_invoice_count", 0),
                    "pending_actions",
                    "text-red-600",
                ),
            ]

            for label, value, icon_name, value_class in metrics:
                with ui.card().classes(
                    "w-full rounded-xl border border-gray-200 shadow-sm p-5"
                ):
                    with ui.row().classes(
                        "w-full items-center justify-between"
                    ):
                        with ui.column().classes("gap-0"):
                            ui.label(label).classes(
                                "text-xs font-bold tracking-wider text-gray-500"
                            )
                            ui.label(str(value)).classes(
                                f"text-3xl font-bold {value_class} mt-2"
                            )
                        ui.icon(icon_name).classes(
                            f"text-3xl {value_class}"
                        )

        # --------------------------------------------------------
        # Analytics
        # --------------------------------------------------------

        ui.label("Analytics").classes(
            "text-xl font-bold text-gray-800 mb-3"
        )

        sales_value = float(financial.get("total_sales") or 0)
        purchases_value = float(financial.get("total_purchases") or 0)

        # Sales vs Purchases
        with ui.card().classes(
            "w-full rounded-xl border border-gray-200 shadow-sm p-5 mb-4"
        ):
            ui.label("Sales vs Purchases").classes(
                "text-lg font-semibold text-gray-800"
            )
            ui.label(
                "Compare total sales and purchase invoice values."
            ).classes(
                "text-sm text-gray-500 mb-2"
            )

            ui.echart(
                {
                    "tooltip": {
                        "trigger": "axis",
                    },
                    "grid": {
                        "left": "5%",
                        "right": "3%",
                        "top": "8%",
                        "bottom": "8%",
                        "containLabel": True,
                    },
                    "xAxis": {
                        "type": "category",
                        "data": ["Sales", "Purchases"],
                    },
                    "yAxis": {
                        "type": "value",
                        "axisLabel": {
                            "formatter": "₹{value}",
                        },
                    },
                    "series": [
                        {
                            "name": "Amount",
                            "type": "bar",
                            "data": [sales_value, purchases_value],
                            "barMaxWidth": 90,
                            "showBackground": True,
                            "backgroundStyle": {
                                "color": "#f3f4f6",
                            },
                            "label": {
                                "show": True,
                                "position": "top",
                                "formatter": "₹{c}",
                            },
                        }
                    ],
                }
            ).classes("w-full h-72")

        with ui.grid(columns=2).classes(
            "w-full gap-4"
        ):

            # ----------------------------------------------------
            # Tax Breakdown
            # ----------------------------------------------------

            with ui.card().classes(
                "w-full rounded-xl border border-gray-200 shadow-sm p-5"
            ):
                ui.label("Tax Breakdown").classes(
                    "text-lg font-semibold text-gray-800"
                )
                ui.label(
                    "Tax contribution by GST type."
                ).classes(
                    "text-sm text-gray-500 mb-2"
                )

                tax_chart_data = []

                for tax_name, tax_key in [
                    ("CGST", "cgst"),
                    ("SGST", "sgst"),
                    ("IGST", "igst"),
                ]:
                    amount = float(tax.get(tax_key) or 0)
                    if amount > 0:
                        tax_chart_data.append(
                            {
                                "name": tax_name,
                                "value": amount,
                            }
                        )

                if tax_chart_data:
                    ui.echart(
                        {
                            "tooltip": {
                                "trigger": "item",
                                "formatter": "{b}: ₹{c} ({d}%)",
                            },
                            "legend": {
                                "orient": "horizontal",
                                "bottom": 0,
                            },
                            "series": [
                                {
                                    "type": "pie",
                                    "radius": ["45%", "72%"],
                                    "avoidLabelOverlap": True,
                                    "itemStyle": {
                                        "borderRadius": 6,
                                        "borderColor": "#ffffff",
                                        "borderWidth": 2,
                                    },
                                    "label": {
                                        "formatter": "{b}\n₹{c}",
                                    },
                                    "data": tax_chart_data,
                                }
                            ],
                        }
                    ).classes("w-full h-72")
                else:
                    with ui.column().classes(
                        "w-full h-72 items-center justify-center"
                    ):
                        ui.icon("pie_chart").classes(
                            "text-5xl text-gray-300"
                        )
                        ui.label(
                            "No tax data available."
                        ).classes(
                            "text-gray-500 mt-2"
                        )

            # ----------------------------------------------------
            # Top Suppliers
            # ----------------------------------------------------

            with ui.card().classes(
                "w-full rounded-xl border border-gray-200 shadow-sm p-5"
            ):
                ui.label("Top Suppliers").classes(
                    "text-lg font-semibold text-gray-800"
                )
                ui.label(
                    "Suppliers ranked by purchase invoice value."
                ).classes(
                    "text-sm text-gray-500 mb-2"
                )

                supplier_rows = sorted(
                    suppliers,
                    key=lambda item: float(
                        item.get("total_amount") or 0
                    ),
                    reverse=True,
                )[:5]

                if supplier_rows:
                    ui.echart(
                        {
                            "tooltip": {
                                "trigger": "axis",
                                "axisPointer": {
                                    "type": "shadow",
                                },
                            },
                            "grid": {
                                "left": "4%",
                                "right": "5%",
                                "top": "5%",
                                "bottom": "8%",
                                "containLabel": True,
                            },
                            "xAxis": {
                                "type": "value",
                                "axisLabel": {
                                    "formatter": "₹{value}",
                                },
                            },
                            "yAxis": {
                                "type": "category",
                                "data": [
                                    row.get("supplier", "-")
                                    for row in reversed(supplier_rows)
                                ],
                                "axisLabel": {
                                    "width": 170,
                                    "overflow": "truncate",
                                },
                            },
                            "series": [
                                {
                                    "type": "bar",
                                    "data": [
                                        float(
                                            row.get("total_amount") or 0
                                        )
                                        for row in reversed(supplier_rows)
                                    ],
                                    "barMaxWidth": 34,
                                    "label": {
                                        "show": True,
                                        "position": "right",
                                        "formatter": "₹{c}",
                                    },
                                }
                            ],
                        }
                    ).classes("w-full h-72")
                else:
                    with ui.column().classes(
                        "w-full h-72 items-center justify-center"
                    ):
                        ui.icon("factory").classes(
                            "text-5xl text-gray-300"
                        )
                        ui.label(
                            "No supplier data available."
                        ).classes(
                            "text-gray-500 mt-2"
                        )

            # ----------------------------------------------------
            # Top Customers
            # ----------------------------------------------------

            with ui.card().classes(
                "w-full rounded-xl border border-gray-200 shadow-sm p-5"
            ):
                ui.label("Top Customers").classes(
                    "text-lg font-semibold text-gray-800"
                )
                ui.label(
                    "Customers ranked by sales invoice value."
                ).classes(
                    "text-sm text-gray-500 mb-2"
                )

                customer_rows = sorted(
                    customers,
                    key=lambda item: float(
                        item.get("total_amount") or 0
                    ),
                    reverse=True,
                )[:5]

                if customer_rows:
                    ui.echart(
                        {
                            "tooltip": {
                                "trigger": "axis",
                                "axisPointer": {
                                    "type": "shadow",
                                },
                            },
                            "grid": {
                                "left": "4%",
                                "right": "5%",
                                "top": "5%",
                                "bottom": "8%",
                                "containLabel": True,
                            },
                            "xAxis": {
                                "type": "value",
                                "axisLabel": {
                                    "formatter": "₹{value}",
                                },
                            },
                            "yAxis": {
                                "type": "category",
                                "data": [
                                    row.get("customer", "-")
                                    for row in reversed(customer_rows)
                                ],
                                "axisLabel": {
                                    "width": 170,
                                    "overflow": "truncate",
                                },
                            },
                            "series": [
                                {
                                    "type": "bar",
                                    "data": [
                                        float(
                                            row.get("total_amount") or 0
                                        )
                                        for row in reversed(customer_rows)
                                    ],
                                    "barMaxWidth": 34,
                                    "label": {
                                        "show": True,
                                        "position": "right",
                                        "formatter": "₹{c}",
                                    },
                                }
                            ],
                        }
                    ).classes("w-full h-72")
                else:
                    with ui.column().classes(
                        "w-full h-72 items-center justify-center"
                    ):
                        ui.icon("groups").classes(
                            "text-5xl text-gray-300"
                        )
                        ui.label(
                            "No customer data available."
                        ).classes(
                            "text-gray-500 mt-2"
                        )

        # --------------------------------------------------------
        # Business Insights
        # --------------------------------------------------------

        ui.label("Business Insights").classes(
            "text-xl font-bold text-gray-800 mt-8 mb-3"
        )

        outstanding_value = float(
            financial.get("outstanding_amount") or 0
        )
        invoice_count = int(
            invoices.get("total_invoice_count", 0) or 0
        )
        unpaid_count = int(
            invoices.get("unpaid_invoice_count", 0) or 0
        )

        purchase_sales_ratio = (
            (purchases_value / sales_value) * 100
            if sales_value > 0
            else 0
        )
        purchase_sales_difference = purchases_value - sales_value

        with ui.grid(columns=3).classes(
            "w-full gap-4 mb-8"
        ):

            with ui.card().classes(
                "w-full rounded-xl border border-red-100 bg-red-50 shadow-sm p-5"
            ):
                ui.icon("account_balance_wallet").classes(
                    "text-3xl text-red-600 mb-3"
                )
                ui.label("Outstanding Payables").classes(
                    "text-sm font-semibold text-gray-600"
                )
                ui.label(
                    format_currency(outstanding_value)
                ).classes(
                    "text-xl font-bold text-red-600 mt-1"
                )
                ui.label(
                    f"{unpaid_count} unpaid purchase invoice(s)"
                ).classes(
                    "text-xs text-gray-500 mt-1"
                )

            with ui.card().classes(
                "w-full rounded-xl border border-gray-200 shadow-sm p-5"
            ):
                ui.icon("compare_arrows").classes(
                    "text-3xl text-blue-600 mb-3"
                )
                ui.label("Purchase-to-Sales Ratio").classes(
                    "text-sm font-semibold text-gray-600"
                )
                ui.label(
                    f"{purchase_sales_ratio:.1f}%"
                ).classes(
                    "text-xl font-bold text-blue-600 mt-1"
                )
                ui.label(
                    "Purchases as a percentage of sales"
                ).classes(
                    "text-xs text-gray-500 mt-1"
                )

            with ui.card().classes(
                "w-full rounded-xl border border-gray-200 shadow-sm p-5"
            ):
                ui.icon("insights").classes(
                    "text-3xl text-gray-700 mb-3"
                )
                ui.label("Sales vs Purchases").classes(
                    "text-sm font-semibold text-gray-600"
                )

                if purchase_sales_difference > 0:
                    insight_text = (
                        f"Purchases exceed sales by "
                        f"{format_currency(purchase_sales_difference)}"
                    )
                elif purchase_sales_difference < 0:
                    insight_text = (
                        f"Sales exceed purchases by "
                        f"{format_currency(abs(purchase_sales_difference))}"
                    )
                else:
                    insight_text = "Sales and purchases are equal."

                ui.label(
                    insight_text
                ).classes(
                    "text-base font-bold text-gray-800 mt-1"
                )
                ui.label(
                    f"{invoice_count} processed invoice(s)"
                ).classes(
                    "text-xs text-gray-500 mt-2"
                )

        # --------------------------------------------------------
        # Quick Actions
        # --------------------------------------------------------

        ui.label("Quick Actions").classes(
            "text-xl font-bold text-gray-800 mt-8 mb-3"
        )

        with ui.row().classes(
            "w-full gap-3 flex-wrap mb-8"
        ):
            ui.button(
                "UPLOAD INVOICE",
                icon="upload_file",
                on_click=lambda: ui.navigate.to("/upload"),
            ).props(
                "color=primary unelevated"
            ).classes(
                "rounded-lg"
            )

            ui.button(
                "VIEW INVOICES",
                icon="receipt",
                on_click=lambda: ui.navigate.to("/invoices"),
            ).props(
                "outline color=primary"
            ).classes(
                "rounded-lg"
            )

# ============================================================
# INVOICES
# ============================================================

@ui.page("/invoices")
def invoices_page():

    header()

    with ui.column().classes(
        "w-full max-w-7xl mx-auto p-8"
    ):

        ui.label("Invoices").classes(
            "text-4xl font-bold"
        )

        ui.label(
            "Search, review and inspect processed invoices."
        ).classes(
            "text-lg text-gray-500 mb-6"
        )

        # ----------------------------------------------------
        # Unified Search
        # ----------------------------------------------------

        with ui.card().classes(
            "w-full mb-6 border border-blue-100 shadow-sm"
        ):

            ui.label(
                "Search Invoices"
            ).classes(
                "text-xl font-semibold"
            )

            ui.label(
                "Search by client name, GSTIN, or invoice number."
            ).classes(
                "text-sm text-gray-500 mb-4"
            )

            with ui.row().classes(
                "w-full items-center gap-3"
            ):

                search_input = ui.input(
                    label="Client Name, GSTIN or Invoice Number",
                    placeholder="e.g. Yara Green Energy, 09AABCY6613M1ZV, or YGEPL/26-27/4",
                ).classes(
                    "flex-1"
                )

                search_button = ui.button(
                    "SEARCH",
                    icon="search",
                ).props(
                    "color=primary"
                )

                reset_button = ui.button(
                    "RESET"
                ).props(
                    "outline"
                )

        results_container = ui.column().classes(
            "w-full"
        )

        # ----------------------------------------------------
        # Invoice table
        # ----------------------------------------------------

        def render_invoice_table(
            invoice_list,
            title=None,
        ):

            if title:
                ui.label(title).classes(
                    "text-lg font-semibold mb-3"
                )

            columns = [
                {
                    "name": "invoice_number",
                    "label": "Invoice Number",
                    "field": "invoice_number",
                    "align": "left",
                },
                {
                    "name": "invoice_type",
                    "label": "Type",
                    "field": "invoice_type",
                    "align": "left",
                },
                {
                    "name": "seller",
                    "label": "Seller",
                    "field": "seller",
                    "align": "left",
                },
                {
                    "name": "buyer",
                    "label": "Buyer",
                    "field": "buyer",
                    "align": "left",
                },
                {
                    "name": "invoice_date",
                    "label": "Date",
                    "field": "invoice_date",
                    "align": "left",
                },
                {
                    "name": "total_amount",
                    "label": "Total",
                    "field": "total_amount",
                    "align": "right",
                },
                {
                    "name": "action",
                    "label": "",
                    "field": "action",
                    "align": "right",
                },
            ]

            rows = []

            for invoice in invoice_list:

                rows.append(
                    {
                        "id": invoice.get("id"),
                        "invoice_number": invoice.get(
                            "invoice_number",
                            "-"
                        ),
                        "invoice_type": invoice.get(
                            "invoice_type",
                            "-"
                        ),
                        "seller": invoice.get(
                            "seller",
                            "-"
                        ),
                        "buyer": invoice.get(
                            "buyer",
                            "-"
                        ),
                        "invoice_date": invoice.get(
                            "invoice_date",
                            "-"
                        ),
                        "total_amount": format_currency(
                            invoice.get(
                                "total_amount",
                                0
                            )
                        ),
                        "action": "",
                    }
                )

            with ui.element("div").classes(
                "w-full overflow-x-auto"
            ):

                table = ui.table(
                    columns=columns,
                    rows=rows,
                    row_key="id",
                ).classes(
                    "w-full"
                )

                table.add_slot(
                    "body-cell-action",
                    """
                    <q-td :props="props">
                        <q-btn
                            flat
                            dense
                            color="primary"
                            label="VIEW"
                            @click="$parent.$emit('view-invoice', props.row.id)"
                        />
                    </q-td>
                    """,
                )

                table.on(
                    "view-invoice",
                    lambda event: ui.navigate.to(
                        f"/invoices/{event.args}"
                    ),
                )

        # ----------------------------------------------------
        # Render unified search results
        # ----------------------------------------------------

        def render_search_results(data):

            results_container.clear()

            clients = data.get(
                "clients",
                []
            )

            total_invoices = sum(
                len(client.get("invoices", []))
                for client in clients
            )

            with results_container:

                ui.label(
                    f"{total_invoices} invoice(s) found"
                ).classes(
                    "text-lg font-semibold mb-3"
                )

                if not clients:

                    ui.label(
                        "No matching invoices or clients found."
                    ).classes(
                        "text-gray-500"
                    )

                    return

                # Client-level searches show the matching client once,
                # followed immediately by only that client's invoices.
                if len(clients) == 1:

                    client = clients[0]

                    with ui.row().classes(
                        "w-full items-end justify-between mb-3"
                    ):

                        with ui.column().classes(
                            "gap-0"
                        ):

                            ui.label(
                                client.get("name", "-")
                            ).classes(
                                "text-lg font-bold"
                            )

                            ui.label(
                                f"GSTIN: {client.get('gstin', '-')}"
                            ).classes(
                                "text-sm text-gray-500"
                            )

                        ui.label(
                            f"{len(client.get('invoices', []))} invoice(s)"
                        ).classes(
                            "text-sm font-semibold text-blue-600"
                        )

                    render_invoice_table(
                        client.get(
                            "invoices",
                            []
                        )
                    )

                    return

                # Multiple matching clients: keep each client grouped,
                # but use the same compact table with integrated View.
                for client in clients:

                    with ui.card().classes(
                        "w-full mb-4 border border-gray-200 shadow-sm"
                    ):

                        with ui.row().classes(
                            "w-full items-end justify-between mb-3"
                        ):

                            with ui.column().classes(
                                "gap-0"
                            ):

                                ui.label(
                                    client.get("name", "-")
                                ).classes(
                                    "text-lg font-bold"
                                )

                                ui.label(
                                    f"GSTIN: {client.get('gstin', '-')}"
                                ).classes(
                                    "text-sm text-gray-500"
                                )

                            ui.label(
                                f"{len(client.get('invoices', []))} invoice(s)"
                            ).classes(
                                "text-sm font-semibold text-blue-600"
                            )

                        render_invoice_table(
                            client.get(
                                "invoices",
                                []
                            )
                        )

        # ----------------------------------------------------
        # Initial / reset list
        # ----------------------------------------------------

        def load_all_invoices():

            data = get_invoices()

            results_container.clear()

            with results_container:

                invoices = data.get(
                    "invoices",
                    []
                )

                ui.label(
                    f"{len(invoices)} invoice(s) found"
                ).classes(
                    "text-lg font-semibold mb-3"
                )

                if not invoices:

                    ui.label(
                        "No invoices found."
                    ).classes(
                        "text-gray-500"
                    )
                    return

                render_invoice_table(
                    invoices
                )

        # ----------------------------------------------------
        # Search action
        # ----------------------------------------------------

        def perform_search():

            term = search_input.value.strip()

            try:

                if not term:
                    load_all_invoices()
                    return

                data = search_clients(
                    term
                )

                render_search_results(
                    data
                )

            except Exception as error:

                show_error(
                    results_container,
                    f"Search failed: {error}",
                )

        search_button.on_click(
            perform_search
        )

        # ----------------------------------------------------
        # Reset
        # ----------------------------------------------------

        def reset_search():

            search_input.value = ""

            try:
                load_all_invoices()

            except Exception as error:

                show_error(
                    results_container,
                    f"Unable to load invoices: {error}",
                )

        reset_button.on_click(
            reset_search
        )

        # ----------------------------------------------------
        # Initial invoice load
        # ----------------------------------------------------

        try:
            load_all_invoices()

        except Exception as error:

            show_error(
                results_container,
                f"Unable to load invoices: {error}",
            )


# ============================================================
# INVOICE DETAIL
# ============================================================

@ui.page("/invoices/{invoice_id}")
def invoice_detail_page(invoice_id: str):

    header()

    with ui.column().classes(
        "w-full max-w-7xl mx-auto p-8"
    ):

        ui.button(
            "← BACK TO INVOICES",
            on_click=lambda: ui.navigate.to(
                "/invoices"
            ),
        ).props(
            "flat"
        ).classes(
            "mb-4"
        )

        try:

            invoice = get_invoice(
                invoice_id
            )

        except Exception as error:

            ui.label(
                f"Unable to load invoice: {error}"
            ).classes(
                "text-red-600 text-lg"
            )

            return

        if not invoice:

            ui.label(
                "Invoice not found."
            ).classes(
                "text-red-600 text-lg"
            )

            return

        ui.label(
            f"Invoice {invoice.get('invoice_number', '-')}"
        ).classes(
            "text-4xl font-bold"
        )

        ui.label(
            "Invoice details and extracted information"
        ).classes(
            "text-lg text-gray-500 mb-6"
        )

        # ----------------------------------------------------
        # Invoice Information
        # ----------------------------------------------------

        with ui.card().classes(
            "w-full"
        ):

            ui.label(
                "Invoice Information"
            ).classes(
                "text-2xl font-semibold mb-4"
            )

            with ui.grid(columns=3).classes(
                "w-full"
            ):

                fields = [
                    (
                        "Invoice Number",
                        invoice.get(
                            "invoice_number",
                            "-"
                        ),
                    ),
                    (
                        "Invoice Type",
                        invoice.get(
                            "invoice_type",
                            "-"
                        ),
                    ),
                    (
                        "Invoice Date",
                        invoice.get(
                            "invoice_date",
                            "-"
                        ),
                    ),
                    (
                        "Due Date",
                        invoice.get(
                            "due_date",
                            "-"
                        ),
                    ),
                    (
                        "Validation Status",
                        invoice.get(
                            "validation_status",
                            "-"
                        ),
                    ),
                    (
                        "Source File",
                        invoice.get(
                            "source_file",
                            "-"
                        ),
                    ),
                ]

                for label, value in fields:

                    with ui.column():

                        ui.label(
                            label
                        ).classes(
                            "text-gray-500"
                        )

                        ui.label(
                            str(value)
                        ).classes(
                            "font-semibold"
                        )

        # ----------------------------------------------------
        # Parties
        # ----------------------------------------------------

        with ui.card().classes(
            "w-full mt-6"
        ):

            ui.label(
                "Parties"
            ).classes(
                "text-2xl font-semibold mb-4"
            )

            with ui.grid(columns=2).classes(
                "w-full"
            ):

                with ui.column():

                    ui.label(
                        "Seller"
                    ).classes(
                        "text-gray-500"
                    )

                    ui.label(
                        invoice.get(
                            "seller",
                            "-"
                        )
                    ).classes(
                        "font-semibold"
                    )

                    ui.label(
                        f"GSTIN: {invoice.get('seller_gstin', '-')}"
                    ).classes(
                        "text-sm text-gray-500"
                    )

                with ui.column():

                    ui.label(
                        "Buyer"
                    ).classes(
                        "text-gray-500"
                    )

                    ui.label(
                        invoice.get(
                            "buyer",
                            "-"
                        )
                    ).classes(
                        "font-semibold"
                    )

                    ui.label(
                        f"GSTIN: {invoice.get('buyer_gstin', '-')}"
                    ).classes(
                        "text-sm text-gray-500"
                    )

        # ----------------------------------------------------
        # Items
        # ----------------------------------------------------

        ui.label(
            "Items"
        ).classes(
            "text-2xl font-semibold mt-8 mb-3"
        )

        items = invoice.get(
            "items",
            []
        )

        item_columns = [
            {
                "name": "item_number",
                "label": "#",
                "field": "item_number",
            },
            {
                "name": "material_name",
                "label": "Material",
                "field": "material_name",
            },
            {
                "name": "hsn",
                "label": "HSN",
                "field": "hsn",
            },
            {
                "name": "quantity",
                "label": "Quantity",
                "field": "quantity",
            },
            {
                "name": "unit",
                "label": "Unit",
                "field": "unit",
            },
            {
                "name": "rate",
                "label": "Rate",
                "field": "rate",
            },
            {
                "name": "taxable_value",
                "label": "Taxable Value",
                "field": "taxable_value",
            },
        ]

        item_rows = []

        for item in items:

            item_rows.append(
                {
                    "item_number": item.get(
                        "item_number"
                    ),
                    "material_name": item.get(
                        "material_name"
                    ),
                    "hsn": item.get(
                        "hsn"
                    ),
                    "quantity": item.get(
                        "quantity"
                    ),
                    "unit": item.get(
                        "unit"
                    ),
                    "rate": format_currency(
                        item.get(
                            "rate"
                        )
                    ),
                    "taxable_value": format_currency(
                        item.get(
                            "taxable_value"
                        )
                    ),
                }
            )

        if item_rows:

            ui.table(
                columns=item_columns,
                rows=item_rows,
                row_key="item_number",
            ).classes(
                "w-full"
            )

        else:

            ui.label(
                "No line items found."
            ).classes(
                "text-gray-500"
            )

        # ----------------------------------------------------
        # Taxes
        # ----------------------------------------------------

        ui.label(
            "Taxes"
        ).classes(
            "text-2xl font-semibold mt-8 mb-3"
        )

        taxes = invoice.get(
            "taxes",
            []
        )

        tax_columns = [
            {
                "name": "tax_type",
                "label": "Tax Type",
                "field": "tax_type",
            },
            {
                "name": "rate",
                "label": "Rate",
                "field": "rate",
            },
            {
                "name": "amount",
                "label": "Amount",
                "field": "amount",
            },
        ]

        tax_rows = []

        for tax in taxes:

            rate = tax.get(
                "rate"
            )

            tax_rows.append(
                {
                    "tax_type": tax.get(
                        "tax_type"
                    ),
                    "rate": (
                        f"{rate}%"
                        if rate is not None
                        else "-"
                    ),
                    "amount": format_currency(
                        tax.get(
                            "amount"
                        )
                    ),
                }
            )

        if tax_rows:

            ui.table(
                columns=tax_columns,
                rows=tax_rows,
                row_key="tax_type",
            ).classes(
                "w-full"
            )

        else:

            ui.label(
                "No tax records found."
            ).classes(
                "text-gray-500"
            )

        # ----------------------------------------------------
        # Totals
        # ----------------------------------------------------

        with ui.card().classes(
            "w-full mt-8"
        ):

            ui.label(
                "Totals"
            ).classes(
                "text-2xl font-semibold mb-4"
            )

            with ui.column().classes(
                "w-full items-end"
            ):

                ui.label(
                    f"Total Tax: "
                    f"{format_currency(invoice.get('total_tax'))}"
                )

                ui.label(
                    f"Round Off: "
                    f"{format_currency(invoice.get('round_off'))}"
                )

                ui.label(
                    f"Received: "
                    f"{format_currency(invoice.get('received_amount'))}"
                )

                ui.label(
                    f"Grand Total: "
                    f"{format_currency(invoice.get('total_amount'))}"
                ).classes(
                    "text-2xl font-bold mt-2"
                )


# ============================================================
# UPLOAD
# ============================================================

@ui.page("/upload")
def upload_page():
    header()

    with ui.column().classes(
        "w-full max-w-5xl mx-auto p-8"
    ):
        ui.label("Upload Invoice").classes(
            "text-4xl font-bold"
        )

        ui.label(
            "Upload a PDF invoice and let InvoiceIQ extract, "
            "validate and store the invoice automatically."
        ).classes(
            "text-lg text-gray-500 mb-8"
        )

        # ----------------------------------------------------
        # Upload Card
        # ----------------------------------------------------

        with ui.card().classes("w-full"):

            ui.label("Upload Invoice PDF").classes(
                "text-2xl font-semibold mb-4"
            )

            ui.label(
                "Only PDF files are supported."
            ).classes(
                "text-gray-500 mb-6"
            )

            result_container = ui.column().classes(
                "w-full mt-6"
            )

            async def handle_upload(event: events.UploadEventArguments):
                result_container.clear()

                with result_container:
                    ui.spinner(size="lg")
                    ui.label(
                        "Processing invoice..."
                    ).classes(
                        "text-lg text-gray-600 mt-3"
                    )

                try:
                    # ----------------------------------------------------
                    # NiceGUI 3.x upload API
                    # ----------------------------------------------------
                    file_name = event.file.name
                    file_content = await event.file.read()

                    # ----------------------------------------------------
                    # Send PDF to FastAPI
                    # Run requests in a worker thread so the UI
                    # does not freeze.
                    # ----------------------------------------------------
                    response = await run.io_bound(
                        upload_invoice,
                        file_name,
                        file_content,
                    )

                    # ----------------------------------------------------
                    # Read API response safely
                    # ----------------------------------------------------
                    try:
                        response_data = response.json()
                    except Exception:
                        response_data = {}

                    # ====================================================
                    # SUCCESS
                    # ====================================================
                    if response.status_code == 200:

                        result_container.clear()

                        with result_container:
                            ui.label(
                                "✓ Invoice Processed Successfully"
                            ).classes(
                                "text-2xl font-bold text-green-600"
                            )

                            ui.label(
                                f"Invoice Number: "
                                f"{response_data.get('invoice_number', '-')}"
                            ).classes(
                                "text-lg mt-3"
                            )

                            ui.label(
                                f"Invoice ID: "
                                f"{response_data.get('invoice_id', '-')}"
                            ).classes(
                                "text-lg"
                            )

                            ui.label(
                                "Validation Status: "
                                f"{response_data.get('validation_status', '-')}"
                            ).classes(
                                "text-lg"
                            )

                            ui.button(
                                "VIEW INVOICE",
                                on_click=lambda invoice_id=response_data.get(
                                    "invoice_id"
                                ): ui.navigate.to(
                                    f"/invoices/{invoice_id}"
                                ),
                            ).props(
                                "color=primary"
                            ).classes(
                                "mt-4"
                            )

                        return

                    # ====================================================
                    # DUPLICATE
                    # ====================================================
                    if response.status_code == 409:

                        result_container.clear()

                        with result_container:
                            ui.label(
                                "⚠ Duplicate Invoice"
                            ).classes(
                                "text-2xl font-bold text-orange-600"
                            )

                            detail = response_data.get(
                                "detail",
                                {}
                            )

                            # FastAPI can return either:
                            #   detail = dict
                            # or
                            #   detail = string
                            if isinstance(detail, dict):
                                invoice_number = detail.get(
                                    "invoice_number",
                                    "-"
                                )

                                existing_id = detail.get(
                                    "existing_invoice_id",
                                    "-"
                                )

                                ui.label(
                                    f"Invoice Number: {invoice_number}"
                                ).classes(
                                    "text-lg mt-3"
                                )

                                ui.label(
                                    f"Existing Invoice ID: {existing_id}"
                                ).classes(
                                    "text-lg"
                                )

                            else:
                                ui.label(
                                    str(detail)
                                ).classes(
                                    "text-red-600 mt-3"
                                )

                        return

                    # ====================================================
                    # VALIDATION / PROCESSING FAILURE
                    # ====================================================
                    if response.status_code == 422:

                        result_container.clear()

                        with result_container:
                            ui.label(
                                "✗ Invoice Could Not Be Processed"
                            ).classes(
                                "text-2xl font-bold text-red-600"
                            )

                            detail = response_data.get(
                                "detail",
                                "Invoice processing failed."
                            )

                            # --------------------------------------------
                            # Case 1:
                            # Validation failure returns a dictionary
                            # --------------------------------------------
                            if isinstance(detail, dict):

                                ui.label(
                                    f"Invoice Number: "
                                    f"{detail.get('invoice_number', '-')}"
                                ).classes(
                                    "text-lg mt-3"
                                )

                                errors = detail.get(
                                    "errors",
                                    []
                                )

                                if errors:
                                    ui.label(
                                        "Validation Errors:"
                                    ).classes(
                                        "font-semibold mt-4"
                                    )

                                    for error in errors:
                                        ui.label(
                                            f"• {error}"
                                        ).classes(
                                            "text-red-600"
                                        )

                                warnings = detail.get(
                                    "warnings",
                                    []
                                )

                                if warnings:
                                    ui.label(
                                        "Warnings:"
                                    ).classes(
                                        "font-semibold mt-4"
                                    )

                                    for warning in warnings:
                                        ui.label(
                                            f"• {warning}"
                                        ).classes(
                                            "text-orange-600"
                                        )

                            # --------------------------------------------
                            # Case 2:
                            # Extraction failure returns a string
                            # --------------------------------------------
                            else:
                                ui.label(
                                    str(detail)
                                ).classes(
                                    "text-red-600 mt-3"
                                )

                        return

                    # ====================================================
                    # OTHER API ERROR
                    # ====================================================
                    result_container.clear()

                    with result_container:
                        ui.label(
                            "✗ Upload Failed"
                        ).classes(
                            "text-2xl font-bold text-red-600"
                        )

                        ui.label(
                            f"HTTP Status: {response.status_code}"
                        ).classes(
                            "text-lg mt-3"
                        )

                        detail = response_data.get(
                            "detail",
                            response.text or "Unknown error"
                        )

                        # Safely display either dict or string
                        if isinstance(detail, dict):
                            ui.label(
                                str(detail)
                            ).classes(
                                "text-red-600 mt-2"
                            )
                        else:
                            ui.label(
                                str(detail)
                            ).classes(
                                "text-red-600 mt-2"
                            )

                except Exception as error:

                    result_container.clear()

                    with result_container:
                        ui.label(
                            "✗ Could Not Process Invoice"
                        ).classes(
                            "text-2xl font-bold text-red-600"
                        )

                        ui.label(
                            str(error)
                        ).classes(
                            "text-red-600 mt-3"
                        )

                        # ----------------------------------------------------
                        # File Upload
                        # ----------------------------------------------------

            ui.upload(
                on_upload=handle_upload,
                auto_upload=True,
                multiple=False,
            ).props(
                "accept=.pdf"
            ).classes(
                "w-full"
            )

        # ----------------------------------------------------
        # Processing Information
        # ----------------------------------------------------

        with ui.card().classes(
            "w-full mt-6"
        ):

            ui.label(
                "What happens after upload?"
            ).classes(
                "text-xl font-semibold mb-4"
            )

            steps = [
                "1. PDF text is extracted",
                "2. Invoice data is parsed",
                "3. Items and taxes are identified",
                "4. Invoice totals are calculated",
                "5. Validation rules are applied",
                "6. Duplicate invoices are detected",
                "7. Valid invoices are stored in Firestore",
                "8. Analytics are automatically updated",
            ]

            for step in steps:

                ui.label(
                    step
                ).classes(
                    "text-gray-700"
                )


# ============================================================
# START SERVER
# ============================================================

ui.run(
    title="InvoiceIQ",
    host="0.0.0.0",
    port=int(
        os.getenv(
            "PORT",
            os.getenv("INVOICEIQ_FRONTEND_PORT", "8080"),
        )
    ),
)
