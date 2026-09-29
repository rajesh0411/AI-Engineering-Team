from __future__ import annotations

import gradio as gr

from backend import (
    TradingService,
    TradingSimulationError,
    holding_to_row,
    portfolio_report_to_summary,
    transaction_to_row,
)

service = TradingService()


def build_account_dropdown(selected_account_id: str | None = None) -> gr.Dropdown:
    account_ids = service.list_accounts()
    return gr.Dropdown(
        choices=account_ids,
        value=selected_account_id if selected_account_id in account_ids else None,
        label="Account",
        interactive=True,
    )


def empty_holdings_rows() -> list[list[object]]:
    return []


def empty_transaction_rows() -> list[list[object]]:
    return []


def build_holdings_rows(account_id: str) -> list[list[object]]:
    if not account_id:
        return empty_holdings_rows()
    return [holding_to_row(h) for h in service.get_holdings(account_id)]


def build_transaction_rows(account_id: str) -> list[list[object]]:
    if not account_id:
        return empty_transaction_rows()
    return [transaction_to_row(t) for t in service.get_transactions(account_id)]


def build_portfolio_summary(account_id: str) -> str:
    if not account_id:
        return "### Portfolio Summary\n\nSelect an account to view the report."
    return portfolio_report_to_summary(service.get_portfolio_report(account_id))


def build_report_outputs(account_id: str) -> tuple[str, list[list[object]], list[list[object]]]:
    if not account_id:
        return (
            "### Portfolio Summary\n\nSelect an account to view the report.",
            empty_holdings_rows(),
            empty_transaction_rows(),
        )
    return build_portfolio_summary(account_id), build_holdings_rows(account_id), build_transaction_rows(account_id)


def _status_ok(message: str) -> str:
    return f"✅ {message}"


def _status_error(message: str) -> str:
    return f"❌ {message}"


def handle_create_account(account_id: str, initial_deposit: float):
    try:
        account = service.create_account(account_id, initial_deposit)
        dropdown = build_account_dropdown(account.account_id)
        summary, holdings, transactions = build_report_outputs(account.account_id)
        return dropdown, _status_ok(f"Created account {account.account_id}"), summary, holdings, transactions
    except TradingSimulationError as exc:
        return build_account_dropdown(account_id), _status_error(str(exc)), "### Portfolio Summary\n\nSelect an account to view the report.", empty_holdings_rows(), empty_transaction_rows()
    except Exception as exc:
        return build_account_dropdown(account_id), _status_error(f"Unexpected error: {exc}"), "### Portfolio Summary\n\nSelect an account to view the report.", empty_holdings_rows(), empty_transaction_rows()


def handle_refresh_accounts() -> gr.Dropdown:
    return build_account_dropdown()


def handle_deposit(account_id: str, amount: float):
    try:
        service.deposit(account_id, amount)
        return _status_ok("Deposit completed"), *build_report_outputs(account_id)
    except TradingSimulationError as exc:
        return _status_error(str(exc)), *build_report_outputs(account_id)
    except Exception as exc:
        return _status_error(f"Unexpected error: {exc}"), *build_report_outputs(account_id)


def handle_withdraw(account_id: str, amount: float):
    try:
        service.withdraw(account_id, amount)
        return _status_ok("Withdrawal completed"), *build_report_outputs(account_id)
    except TradingSimulationError as exc:
        return _status_error(str(exc)), *build_report_outputs(account_id)
    except Exception as exc:
        return _status_error(f"Unexpected error: {exc}"), *build_report_outputs(account_id)


def handle_buy(account_id: str, symbol: str, quantity: float):
    try:
        service.buy(account_id, symbol, int(quantity))
        return _status_ok("Buy order completed"), *build_report_outputs(account_id)
    except TradingSimulationError as exc:
        return _status_error(str(exc)), *build_report_outputs(account_id)
    except Exception as exc:
        return _status_error(f"Unexpected error: {exc}"), *build_report_outputs(account_id)


def handle_sell(account_id: str, symbol: str, quantity: float):
    try:
        service.sell(account_id, symbol, int(quantity))
        return _status_ok("Sell order completed"), *build_report_outputs(account_id)
    except TradingSimulationError as exc:
        return _status_error(str(exc)), *build_report_outputs(account_id)
    except Exception as exc:
        return _status_error(f"Unexpected error: {exc}"), *build_report_outputs(account_id)


def handle_refresh_report(account_id: str):
    try:
        summary, holdings, transactions = build_report_outputs(account_id)
        return summary, holdings, transactions, _status_ok("Report refreshed")
    except TradingSimulationError as exc:
        return "### Portfolio Summary\n\nSelect an account to view the report.", empty_holdings_rows(), empty_transaction_rows(), _status_error(str(exc))
    except Exception as exc:
        return "### Portfolio Summary\n\nSelect an account to view the report.", empty_holdings_rows(), empty_transaction_rows(), _status_error(f"Unexpected error: {exc}")


with gr.Blocks(title="Trading Simulation Account Manager") as demo:
    gr.Markdown("# Trading Simulation Account Manager")
    gr.Markdown(
        "A polished in-memory account manager for a trading simulation. Create an account, add or withdraw cash, buy and sell shares, and inspect holdings and transaction history."
    )

    with gr.Row():
        with gr.Column():
            gr.Markdown("## Account Management")
            account_id_input = gr.Textbox(label="New Account ID", placeholder="e.g. alice")
            initial_deposit_input = gr.Number(label="Initial Deposit", precision=2, value=10000)
            create_account_button = gr.Button("Create Account", variant="primary")
            refresh_accounts_button = gr.Button("Refresh Accounts")
            account_dropdown = gr.Dropdown(choices=[], label="Account", interactive=True)

        with gr.Column():
            gr.Markdown("## Cash Operations")
            deposit_amount_input = gr.Number(label="Deposit Amount", precision=2, value=1000)
            deposit_button = gr.Button("Deposit", variant="primary")
            withdraw_amount_input = gr.Number(label="Withdraw Amount", precision=2, value=100)
            withdraw_button = gr.Button("Withdraw")

        with gr.Column():
            gr.Markdown("## Trading")
            symbol_dropdown = gr.Dropdown(choices=["AAPL", "TSLA", "GOOGL"], value="AAPL", label="Symbol", interactive=True)
            quantity_input = gr.Number(label="Quantity", precision=0, value=1)
            buy_button = gr.Button("Buy", variant="primary")
            sell_button = gr.Button("Sell")

    gr.Markdown("## Reports")
    refresh_report_button = gr.Button("Refresh Report")
    status_markdown = gr.Markdown()
    portfolio_summary_markdown = gr.Markdown("### Portfolio Summary\n\nSelect an account to view the report.")
    holdings_dataframe = gr.Dataframe(
        headers=["Symbol", "Quantity", "Current Price", "Market Value"],
        datatype=["str", "number", "str", "str"],
        label="Holdings",
        interactive=False,
    )
    transactions_dataframe = gr.Dataframe(
        headers=["Timestamp", "Type", "Symbol", "Quantity", "Share Price", "Amount", "Total Value"],
        datatype=["str", "str", "str", "number", "str", "str", "str"],
        label="Transactions",
        interactive=False,
    )

    create_account_button.click(
        fn=handle_create_account,
        inputs=[account_id_input, initial_deposit_input],
        outputs=[account_dropdown, status_markdown, portfolio_summary_markdown, holdings_dataframe, transactions_dataframe],
    )
    refresh_accounts_button.click(fn=handle_refresh_accounts, inputs=[], outputs=[account_dropdown])
    deposit_button.click(
        fn=handle_deposit,
        inputs=[account_dropdown, deposit_amount_input],
        outputs=[status_markdown, portfolio_summary_markdown, holdings_dataframe, transactions_dataframe],
    )
    withdraw_button.click(
        fn=handle_withdraw,
        inputs=[account_dropdown, withdraw_amount_input],
        outputs=[status_markdown, portfolio_summary_markdown, holdings_dataframe, transactions_dataframe],
    )
    buy_button.click(
        fn=handle_buy,
        inputs=[account_dropdown, symbol_dropdown, quantity_input],
        outputs=[status_markdown, portfolio_summary_markdown, holdings_dataframe, transactions_dataframe],
    )
    sell_button.click(
        fn=handle_sell,
        inputs=[account_dropdown, symbol_dropdown, quantity_input],
        outputs=[status_markdown, portfolio_summary_markdown, holdings_dataframe, transactions_dataframe],
    )
    refresh_report_button.click(
        fn=handle_refresh_report,
        inputs=[account_dropdown],
        outputs=[portfolio_summary_markdown, holdings_dataframe, transactions_dataframe, status_markdown],
    )


if __name__ == "__main__":
    demo.launch()
