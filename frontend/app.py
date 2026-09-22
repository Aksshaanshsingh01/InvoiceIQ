from nicegui import events, run, ui

ui.add_head_html(
    '<link href="https://fonts.googleapis.com/icon?family=Material+Icons" '
    'rel="stylesheet">',
    shared=True,
)

from frontend.api_client import (
    get_dashboard,
    get_invoices,
    get_invoice,
    search_invoices,
    search_clients,
    upload_invoice,
    delete_invoice,
    record_payment,
    get_payment_history,
)

from datetime import datetime, date

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

                # --------------------------------------------------------
        # Receivables Due & Overdue
        # --------------------------------------------------------

        try:
            invoice_data = get_invoices()

            all_invoices = invoice_data.get(
                "invoices",
                []
            )

            today = date.today()
            receivables = []

            for invoice in all_invoices:

                # Only sales invoices are customer receivables.
                if invoice.get("invoice_type") != "SALE":
                    continue

                total_amount = float(
                    invoice.get("total_amount") or 0
                )

                received_amount = float(
                    invoice.get("received_amount") or 0
                )

                outstanding_amount = max(
                    total_amount - received_amount,
                    0,
                )

                # Fully paid invoices should never appear here.
                if outstanding_amount <= 0.01:
                    continue

                due_date_text = str(
                    invoice.get("due_date") or ""
                ).strip()

                if not due_date_text:
                    continue

                try:
                    due_date = datetime.strptime(
                        due_date_text,
                        "%d/%m/%Y"
                    ).date()
                except ValueError:
                    continue

                days_difference = (
                    due_date - today
                ).days

                payment_status = (
                    invoice.get("payment_status")
                    or (
                        "PARTIALLY_PAID"
                        if received_amount > 0
                        else "UNPAID"
                    )
                )

                receivables.append(
                    {
                        "invoice_id": invoice.get("id"),
                        "invoice_number": invoice.get(
                            "invoice_number",
                            "-"
                        ),
                        "customer": invoice.get(
                            "buyer",
                            "-"
                        ),
                        "due_date": due_date,
                        "due_date_text": due_date.strftime(
                            "%d/%m/%Y"
                        ),
                        "outstanding_amount": outstanding_amount,
                        "payment_status": payment_status,
                        "days_difference": days_difference,
                    }
                )

            # ----------------------------------------------------
            # Sort:
            # 1. Overdue first
            # 2. Then earliest upcoming due date
            # ----------------------------------------------------

            receivables.sort(
                key=lambda item: item["due_date"]
            )

        except Exception:
            receivables = []

        with ui.card().classes(
            "w-full rounded-xl border border-gray-200 "
            "shadow-sm p-5 mb-4"
        ):

            ui.label(
                "Receivables Due & Overdue"
            ).classes(
                "text-lg font-semibold text-gray-800"
            )

            ui.label(
                "Outstanding customer payments based on invoice due dates."
            ).classes(
                "text-sm text-gray-500 mb-4"
            )

            if receivables:

                due_date_columns = [
                    {
                        "name": "customer",
                        "label": "Customer",
                        "field": "customer",
                        "align": "left",
                    },
                    {
                        "name": "invoice_number",
                        "label": "Invoice",
                        "field": "invoice_number",
                        "align": "left",
                    },
                    {
                        "name": "due_date",
                        "label": "Due Date",
                        "field": "due_date",
                        "align": "left",
                    },
                    {
                        "name": "amount",
                        "label": "Outstanding",
                        "field": "amount",
                        "align": "right",
                    },
                    {
                        "name": "payment",
                        "label": "Payment",
                        "field": "payment",
                        "align": "left",
                    },
                    {
                        "name": "status",
                        "label": "Due Status",
                        "field": "status",
                        "align": "left",
                    },
                ]

                due_date_rows = []

                for item in receivables:

                    days = item[
                        "days_difference"
                    ]

                    payment_status = item[
                        "payment_status"
                    ]

                    # ------------------------------------------------
                    # Due-date status
                    # ------------------------------------------------

                    if days < 0:
                        overdue_days = abs(days)

                        if overdue_days == 1:
                            due_status = "1 day overdue"
                        else:
                            due_status = (
                                f"{overdue_days} days overdue"
                            )

                    elif days == 0:
                        due_status = "Due today"

                    elif days == 1:
                        due_status = "Due tomorrow"

                    else:
                        due_status = f"Due in {days} days"

                    # ------------------------------------------------
                    # Payment status label
                    # ------------------------------------------------

                    if payment_status == "PAID":
                        payment_label = "PAID"

                    elif payment_status == "PARTIALLY_PAID":
                        payment_label = "PARTIALLY PAID"

                    else:
                        payment_label = "UNPAID"

                    due_date_rows.append(
                        {
                            "id": item["invoice_id"],
                            "customer": item["customer"],
                            "invoice_number": item[
                                "invoice_number"
                            ],
                            "due_date": item[
                                "due_date_text"
                            ],
                            "amount": format_currency(
                                item[
                                    "outstanding_amount"
                                ]
                            ),
                            "payment": payment_label,
                            "status": due_status,
                        }
                    )

                # ----------------------------------------------------
                # Table styling
                # ----------------------------------------------------

                ui.add_css("""
                .upcoming-due-table .q-table {
                    width: 100%;
                    table-layout: fixed;
                }

                /* Customer */
                .upcoming-due-table th:nth-child(1),
                .upcoming-due-table td:nth-child(1) {
                    width: 28%;
                    min-width: 0;
                }

                /* Invoice */
                .upcoming-due-table th:nth-child(2),
                .upcoming-due-table td:nth-child(2) {
                    width: 17%;
                    min-width: 0;
                }

                /* Due Date */
                .upcoming-due-table th:nth-child(3),
                .upcoming-due-table td:nth-child(3) {
                    width: 13%;
                    min-width: 0;
                }

                /* Outstanding */
                .upcoming-due-table th:nth-child(4),
                .upcoming-due-table td:nth-child(4) {
                    width: 17%;
                    min-width: 0;
                    padding-right: 20px;
                }

                /* Payment */
                .upcoming-due-table th:nth-child(5),
                .upcoming-due-table td:nth-child(5) {
                    width: 13%;
                    min-width: 0;
                    padding-left: 10px;
                }

                /* Due Status */
                .upcoming-due-table th:nth-child(6),
                .upcoming-due-table td:nth-child(6) {
                    width: 12%;
                    min-width: 0;
                    padding-left: 10px;
                }

                /* Prevent long customer names from breaking the table. */
                .upcoming-due-table td:nth-child(1) {
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }

                /* Keep invoice/date/payment/status values on one line. */
                .upcoming-due-table td:nth-child(2),
                .upcoming-due-table td:nth-child(3),
                .upcoming-due-table td:nth-child(5),
                .upcoming-due-table td:nth-child(6) {
                    white-space: nowrap;
                }

                /* Keep currency aligned cleanly. */
                .upcoming-due-table td:nth-child(4) {
                    white-space: nowrap;
                }
                """)

                ui.table(
                    columns=due_date_columns,
                    rows=due_date_rows,
                    row_key="id",
                ).classes(
                    "w-full upcoming-due-table"
                )

            else:

                with ui.column().classes(
                    "w-full items-center justify-center py-8"
                ):

                    ui.icon(
                        "event_available"
                    ).classes(
                        "text-5xl text-gray-300"
                    )

                    ui.label(
                        "No outstanding sales receivables."
                    ).classes(
                        "text-gray-500 mt-2"
                    ) 

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

        # ----------------------------------------------------
        # Delete Invoice
        # ----------------------------------------------------

        async def perform_delete():
            try:
                response = await run.io_bound(
                    delete_invoice,
                    invoice_id,
                )

                if response.status_code == 200:
                    ui.notify(
                        "Invoice deleted successfully.",
                        type="positive",
                    )

                    ui.navigate.to("/invoices")
                    return

                if response.status_code == 404:
                    ui.notify(
                        "Invoice no longer exists.",
                        type="warning",
                    )

                    ui.navigate.to("/invoices")
                    return

                try:
                    error_data = response.json()
                    error_message = error_data.get(
                        "detail",
                        response.text,
                    )
                except Exception:
                    error_message = response.text

                ui.notify(
                    f"Failed to delete invoice: {error_message}",
                    type="negative",
                )

            except Exception as error:
                ui.notify(
                    f"Unable to delete invoice: {error}",
                    type="negative",
                )

        with ui.row().classes(
            "w-full items-center justify-between mb-6"
        ):
            ui.label(
                f"Invoice {invoice.get('invoice_number', '-')}"
            ).classes(
                "text-4xl font-bold"
            )

            with ui.dialog() as delete_dialog, ui.card().classes(
                "w-full max-w-md"
            ):
                ui.label(
                    "Delete Invoice?"
                ).classes(
                    "text-2xl font-bold text-red-600"
                )

                ui.label(
                    "This action permanently removes this invoice "
                    "and its extracted items and tax records."
                ).classes(
                    "text-gray-600 mt-3"
                )

                ui.label(
                    f"Invoice: "
                    f"{invoice.get('invoice_number', '-')}"
                ).classes(
                    "font-semibold mt-3"
                )

                with ui.row().classes(
                    "w-full justify-end gap-3 mt-6"
                ):
                    ui.button(
                        "CANCEL",
                        on_click=delete_dialog.close,
                    ).props(
                        "outline"
                    )

                    ui.button(
                        "DELETE",
                        on_click=perform_delete,
                    ).props(
                        "color=negative unelevated"
                    )

            ui.button(
                "DELETE INVOICE",
                icon="delete",
                on_click=delete_dialog.open,
            ).props(
                "color=negative unelevated"
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

            # ------------------------------------------------
            # Core invoice information
            # ------------------------------------------------

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
                ]

                for label, value in fields:

                    with ui.column().classes(
                        "min-w-0"
                    ):

                        ui.label(
                            label
                        ).classes(
                            "text-gray-500"
                        )

                        ui.label(
                            str(value)
                        ).classes(
                            "font-semibold break-words"
                        )

            # ------------------------------------------------
            # Source file
            # ------------------------------------------------

        source_file = str(
                invoice.get(
                    "source_file",
                    "-"
                )
            )

            # Show only the filename, not the internal
            # server filesystem path.
        source_filename = (
            source_file
            .replace("\\", "/")
            .rsplit("/", 1)[-1]
            )

        with ui.column().classes(
            "w-full mt-5"
            ):

                ui.label(
                    "Source File"
                ).classes(
                    "text-gray-500"
                )

                ui.label(
                    f"📄 {source_filename}"
                ).classes(
                    "font-semibold "
                    "break-all "
                    "whitespace-normal "
                    "w-full"
                )

                ui.tooltip(
                    source_file
                ).classes(
                    "max-w-xl break-all"
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
        # Payment & Totals
        # ----------------------------------------------------

        total_amount = float(
            invoice.get("total_amount") or 0
        )

        received_amount = float(
            invoice.get("received_amount") or 0
        )

        outstanding_amount = max(
            total_amount - received_amount,
            0,
        )

        payment_status = (
            invoice.get("payment_status")
            or (
                "PAID"
                if outstanding_amount <= 0.01
                else (
                    "PARTIALLY_PAID"
                    if received_amount > 0
                    else "UNPAID"
                )
            )
        )

        status_labels = {
            "PAID": "PAID",
            "PARTIALLY_PAID": "PARTIALLY PAID",
            "UNPAID": "UNPAID",
        }

        status_classes = {
            "PAID": "text-green-600",
            "PARTIALLY_PAID": "text-orange-600",
            "UNPAID": "text-red-600",
        }

        status_label = status_labels.get(
            payment_status,
            payment_status,
        )

        status_class = status_classes.get(
            payment_status,
            "text-gray-600",
        )

        # ----------------------------------------------------
        # Record Payment
        # ----------------------------------------------------

        async def perform_payment(
            payment_dialog,
            amount_input,
            method_input,
            reference_input,
            notes_input,
        ):
            try:
                amount_text = str(
                    amount_input.value or ""
                ).strip()

                if not amount_text:
                    ui.notify(
                        "Please enter a payment amount.",
                        type="warning",
                    )
                    return

                try:
                    payment_amount = float(
                        amount_text.replace(",", "")
                    )
                except ValueError:
                    ui.notify(
                        "Please enter a valid payment amount.",
                        type="negative",
                    )
                    return

                if payment_amount <= 0:
                    ui.notify(
                        "Payment amount must be greater than zero.",
                        type="warning",
                    )
                    return

                payment_method = (
                    method_input.value
                    if method_input.value
                    else None
                )

                reference = (
                    str(reference_input.value).strip()
                    if reference_input.value
                    else None
                )

                notes = (
                    str(notes_input.value).strip()
                    if notes_input.value
                    else None
                )

                response = await run.io_bound(
                    record_payment,
                    invoice_id,
                    payment_amount,
                    payment_method,
                    reference,
                    notes,
                )

                if response.status_code == 200:
                    ui.notify(
                        "Payment recorded successfully.",
                        type="positive",
                    )

                    payment_dialog.close()

                    # Reload the invoice page so all payment
                    # figures and payment history come from the API.
                    ui.navigate.to(
                        f"/invoices/{invoice_id}"
                    )
                    return

                try:
                    error_data = response.json()
                    error_message = error_data.get(
                        "detail",
                        response.text,
                    )
                except Exception:
                    error_message = response.text

                ui.notify(
                    f"Payment failed: {error_message}",
                    type="negative",
                )

            except Exception as error:
                ui.notify(
                    f"Unable to record payment: {error}",
                    type="negative",
                )

        # ----------------------------------------------------
        # Payment Summary Card
        # ----------------------------------------------------

        with ui.card().classes(
            "w-full mt-8 border border-gray-200 shadow-sm"
        ):

            with ui.row().classes(
                "w-full items-center justify-between mb-5"
            ):

                ui.label(
                    "Payment & Totals"
                ).classes(
                    "text-2xl font-semibold"
                )

                # ------------------------------------------------
                # Record Payment Dialog
                # ------------------------------------------------

                with ui.dialog() as payment_dialog, ui.card().classes(
                    "w-full max-w-md"
                ):

                    ui.label(
                        "Record Payment"
                    ).classes(
                        "text-2xl font-bold"
                    )

                    ui.label(
                        f"Invoice: "
                        f"{invoice.get('invoice_number', '-')}"
                    ).classes(
                        "text-gray-500 mt-2"
                    )

                    ui.label(
                        f"Outstanding: "
                        f"{format_currency(outstanding_amount)}"
                    ).classes(
                        "font-semibold text-red-600 mt-4"
                    )

                    amount_input = ui.input(
                        label="Payment Amount",
                        placeholder="e.g. 10000",
                    ).props(
                        "type=number min=0 step=0.01"
                    ).classes(
                        "w-full mt-3"
                    )

                    method_input = ui.select(
                        [
                            "Bank Transfer",
                            "UPI",
                            "Cash",
                            "Cheque",
                            "Other",
                        ],
                        label="Payment Method",
                        clearable=True,
                    ).classes(
                        "w-full mt-3"
                    )

                    reference_input = ui.input(
                        label="Reference",
                        placeholder="e.g. NEFT123 / UPI reference",
                    ).classes(
                        "w-full mt-3"
                    )

                    notes_input = ui.input(
                        label="Notes",
                        placeholder="Optional notes",
                    ).classes(
                        "w-full mt-3"
                    )

                    with ui.row().classes(
                        "w-full justify-end gap-3 mt-5"
                    ):

                        ui.button(
                            "CANCEL",
                            on_click=payment_dialog.close,
                        ).props(
                            "outline"
                        )

                        ui.button(
                            "RECORD PAYMENT",
                            icon="payments",
                            on_click=lambda: perform_payment(
                                payment_dialog,
                                amount_input,
                                method_input,
                                reference_input,
                                notes_input,
                            ),
                        ).props(
                            "color=primary unelevated"
                        )

                # ------------------------------------------------
                # Record Payment Button
                # ------------------------------------------------

                if outstanding_amount > 0.01:
                    ui.button(
                        "RECORD PAYMENT",
                        icon="payments",
                        on_click=payment_dialog.open,
                    ).props(
                        "color=primary unelevated"
                    ).classes(
                        "rounded-lg"
                    )
                else:
                    ui.button(
                        "FULLY PAID",
                        icon="check_circle",
                    ).props(
                        "color=positive outline"
                    ).classes(
                        "rounded-lg"
                    )

            # ----------------------------------------------------
            # Payment Summary
            # ----------------------------------------------------

            with ui.grid(columns=4).classes(
                "w-full gap-4 mb-6"
            ):

                with ui.card().classes(
                    "border border-gray-200 shadow-none p-4"
                ):
                    ui.label(
                        "GRAND TOTAL"
                    ).classes(
                        "text-xs font-bold tracking-wider text-gray-500"
                    )

                    ui.label(
                        format_currency(total_amount)
                    ).classes(
                        "text-xl font-bold mt-2"
                    )

                with ui.card().classes(
                    "border border-gray-200 shadow-none p-4"
                ):
                    ui.label(
                        "RECEIVED"
                    ).classes(
                        "text-xs font-bold tracking-wider text-gray-500"
                    )

                    ui.label(
                        format_currency(received_amount)
                    ).classes(
                        "text-xl font-bold text-green-600 mt-2"
                    )

                with ui.card().classes(
                    "border border-gray-200 shadow-none p-4"
                ):
                    ui.label(
                        "OUTSTANDING"
                    ).classes(
                        "text-xs font-bold tracking-wider text-gray-500"
                    )

                    ui.label(
                        format_currency(outstanding_amount)
                    ).classes(
                        f"text-xl font-bold "
                        f"{'text-green-600' if outstanding_amount <= 0.01 else 'text-red-600'} "
                        "mt-2"
                    )

                with ui.card().classes(
                    "border border-gray-200 shadow-none p-4"
                ):
                    ui.label(
                        "PAYMENT STATUS"
                    ).classes(
                        "text-xs font-bold tracking-wider text-gray-500"
                    )

                    ui.label(
                        status_label
                    ).classes(
                        f"text-xl font-bold {status_class} mt-2"
                    )

            # ----------------------------------------------------
            # Existing invoice totals
            # ----------------------------------------------------

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
                    f"Grand Total: "
                    f"{format_currency(total_amount)}"
                ).classes(
                    "text-2xl font-bold mt-2"
                )

                if payment_status == "PAID":
                    paid_at = invoice.get("paid_at")

                    if paid_at:
                        ui.label(
                            f"Paid at: {paid_at}"
                        ).classes(
                            "text-sm text-green-600 mt-1"
                        )

        # ----------------------------------------------------
        # Payment History
        # ----------------------------------------------------

        with ui.card().classes(
            "w-full mt-6 border border-gray-200 shadow-sm"
        ):
            ui.label(
                "Payment History"
            ).classes(
                "text-2xl font-semibold mb-1"
            )

            ui.label(
                "Individual payment transactions recorded against this invoice."
            ).classes(
                "text-sm text-gray-500 mb-4"
            )

            try:
                payment_response = get_payment_history(
                    invoice_id
                )

                if payment_response.status_code == 200:
                    payment_data = payment_response.json()
                    payments = payment_data.get(
                        "payments",
                        []
                    )

                    if payments:
                        payment_columns = [
                            {
                                "name": "payment_date",
                                "label": "Date",
                                "field": "payment_date",
                                "align": "left",
                            },
                            {
                                "name": "payment_amount",
                                "label": "Amount",
                                "field": "payment_amount",
                                "align": "right",
                            },
                            {
                                "name": "payment_method",
                                "label": "Method",
                                "field": "payment_method",
                                "align": "left",
                            },
                            {
                                "name": "reference",
                                "label": "Reference",
                                "field": "reference",
                                "align": "left",
                            },
                            {
                                "name": "notes",
                                "label": "Notes",
                                "field": "notes",
                                "align": "left",
                            },
                        ]

                        payment_rows = []

                        for payment in payments:
                            payment_date = str(
                                payment.get(
                                    "payment_date",
                                    "-"
                                )
                            )

                            if "T" in payment_date:
                                payment_date = (
                                    payment_date
                                    .split("T")[0]
                                )

                            payment_rows.append({
                                "payment_date": payment_date,
                                "payment_amount": format_currency(
                                    float(
                                        payment.get(
                                            "payment_amount"
                                        ) or 0
                                    )
                                ),
                                "payment_method": (
                                    payment.get(
                                        "payment_method"
                                    )
                                    or "-"
                                ),
                                "reference": (
                                    payment.get(
                                        "reference"
                                    )
                                    or "-"
                                ),
                                "notes": (
                                    payment.get(
                                        "notes"
                                    )
                                    or "-"
                                ),
                            })

                        with ui.element("div").classes(
                            "w-full overflow-x-auto"
                        ):
                            ui.table(
                                columns=payment_columns,
                                rows=payment_rows,
                                row_key="payment_date",
                            ).classes(
                                "w-full"
                            )

                    else:
                        with ui.column().classes(
                            "w-full items-center justify-center py-8"
                        ):
                            ui.icon(
                                "payments"
                            ).classes(
                                "text-5xl text-gray-300"
                            )

                            ui.label(
                                "No payment transactions recorded yet."
                            ).classes(
                                "text-gray-500 mt-2"
                            )

                else:
                    try:
                        error_data = payment_response.json()
                        error_message = error_data.get(
                            "detail",
                            payment_response.text,
                        )
                    except Exception:
                        error_message = payment_response.text

                    ui.label(
                        f"Unable to load payment history: "
                        f"{error_message}"
                    ).classes(
                        "text-red-500"
                    )

            except Exception as error:
                ui.label(
                    f"Unable to load payment history: {error}"
                ).classes(
                    "text-red-500"
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
