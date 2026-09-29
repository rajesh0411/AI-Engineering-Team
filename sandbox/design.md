# Design: Trading Simulation Account Management System

## 1. Goals

Build a simple in-memory trading simulation platform that supports:

- Creating user accounts with an initial deposit.
- Depositing and withdrawing cash.
- Buying and selling shares by symbol and quantity.
- Preventing invalid operations:
  - Withdrawals that would make cash negative.
  - Buys that exceed available cash.
  - Sells that exceed current holdings.
- Reporting:
  - Current holdings.
  - Holdings at a point in time.
  - Current profit/loss.
  - Profit/loss at a point in time.
  - Portfolio total value.
  - Full transaction history.

All files must live in the same directory.

Expected files:

```text
backend.py
app.py
test_backend.py
```

No third-party dependencies should be used except `gradio`, which is already installed in the `uv` project.

---

## 2. Architecture Overview

The system will be split into three layers:

1. **Backend domain/service layer** — `backend.py`
   - Owns all business logic.
   - Maintains accounts and transactions in memory.
   - Performs validation.
   - Calculates balances, holdings, portfolio value, and profit/loss.

2. **Frontend Gradio app** — `app.py`
   - Provides a simple UI for interacting with the backend.
   - Lets users create accounts, deposit, withdraw, buy, sell, and view reports.
   - Uses Gradio 6 Blocks API.

3. **Unit tests** — `test_backend.py`
   - Tests backend behavior independently of Gradio.
   - Uses Python standard library `unittest`.

---

## 3. Backend Design: `backend.py`

### 3.1 Constants

```python
SUPPORTED_PRICES: dict[str, str]
```

Fixed test prices as strings to preserve Decimal precision.

Expected values:

```text
AAPL  -> 150.00
TSLA  -> 250.00
GOOGL -> 2800.00
```

---

### 3.2 Enums

#### `TransactionType`

Represents supported transaction types.

```python
class TransactionType(str, Enum):
    CREATE_ACCOUNT = "CREATE_ACCOUNT"
    DEPOSIT = "DEPOSIT"
    WITHDRAW = "WITHDRAW"
    BUY = "BUY"
    SELL = "SELL"
```

---

### 3.3 Exceptions

Use explicit domain exceptions so frontend and tests can handle errors cleanly.

```python
class TradingSimulationError(Exception):
    pass
```

```python
class AccountNotFoundError(TradingSimulationError):
    pass
```

```python
class DuplicateAccountError(TradingSimulationError):
    pass
```

```python
class InvalidAmountError(TradingSimulationError):
    pass
```

```python
class InvalidQuantityError(TradingSimulationError):
    pass
```

```python
class UnsupportedSymbolError(TradingSimulationError):
    pass
```

```python
class InsufficientFundsError(TradingSimulationError):
    pass
```

```python
class InsufficientSharesError(TradingSimulationError):
    pass
```

---

### 3.4 Data Classes

#### `Transaction`

Represents one immutable account event.

```python
@dataclass(frozen=True)
class Transaction:
    transaction_id: str
    account_id: str
    transaction_type: TransactionType
    timestamp: datetime
    amount: Decimal | None = None
    symbol: str | None = None
    quantity: int | None = None
    share_price: Decimal | None = None
    total_value: Decimal | None = None
```

Field meanings:

- `amount`: Used for deposits, withdrawals, and initial account creation.
- `symbol`: Used for buy/sell transactions.
- `quantity`: Used for buy/sell transactions.
- `share_price`: Price captured at transaction time.
- `total_value`: `quantity * share_price` for buy/sell transactions.

---

#### `Account`

Represents a trading account.

```python
@dataclass
class Account:
    account_id: str
    created_at: datetime
    initial_deposit: Decimal
    transactions: list[Transaction]
```

Important:

- The account should not store derived balances directly.
- Cash balance, holdings, and portfolio value should be calculated from transactions.
- This makes historical reporting easier and deterministic.

---

#### `Holding`

Represents one stock holding in a report.

```python
@dataclass(frozen=True)
class Holding:
    symbol: str
    quantity: int
    current_price: Decimal
    market_value: Decimal
```

---

#### `PortfolioReport`

Represents a full portfolio snapshot.

```python
@dataclass(frozen=True)
class PortfolioReport:
    account_id: str
    as_of: datetime
    cash_balance: Decimal
    holdings: list[Holding]
    holdings_value: Decimal
    total_value: Decimal
    net_contributions: Decimal
    initial_deposit: Decimal
    profit_loss: Decimal
    profit_loss_vs_initial_deposit: Decimal
```

Definitions:

- `cash_balance`: Available cash.
- `holdings_value`: Current market value of held shares.
- `total_value`: `cash_balance + holdings_value`.
- `net_contributions`: Deposits minus withdrawals as of the report time.
- `profit_loss`: `total_value - net_contributions`.
  - This is the financially accurate profit/loss.
- `profit_loss_vs_initial_deposit`: `total_value - initial_deposit`.
  - This directly supports the requirement to calculate P/L from the initial deposit.

---

### 3.5 Price Function

The system has access to a function called `get_share_price(symbol)`.

The backend engineer should provide the fixed test implementation here.

```python
def get_share_price(symbol: str) -> Decimal:
    """Return the current fixed share price for AAPL, TSLA, or GOOGL."""
```

Behavior:

- Normalize `symbol` to uppercase.
- Return a `Decimal`.
- Raise `UnsupportedSymbolError` for unsupported symbols.

---

### 3.6 Service Class

#### `TradingService`

Main in-memory backend API.

```python
class TradingService:
    def __init__(self) -> None:
        ...
```

Internal state:

```python
self._accounts: dict[str, Account]
```

---

### 3.7 Account Methods

#### Create Account

```python
def create_account(
    self,
    account_id: str,
    initial_deposit: Decimal | int | float | str,
    timestamp: datetime | None = None,
) -> Account:
    ...
```

Behavior:

- Validate `account_id` is not empty.
- Validate account does not already exist.
- Validate `initial_deposit > 0`.
- Create account.
- Add a `CREATE_ACCOUNT` transaction with `amount=initial_deposit`.
- Return created account.

Raises:

- `DuplicateAccountError`
- `InvalidAmountError`

---

#### Get Account

```python
def get_account(self, account_id: str) -> Account:
    ...
```

Behavior:

- Return account by ID.
- Raise `AccountNotFoundError` if missing.

---

#### List Accounts

```python
def list_accounts(self) -> list[str]:
    ...
```

Behavior:

- Return account IDs sorted alphabetically.

---

### 3.8 Cash Methods

#### Deposit

```python
def deposit(
    self,
    account_id: str,
    amount: Decimal | int | float | str,
    timestamp: datetime | None = None,
) -> Transaction:
    ...
```

Behavior:

- Validate account exists.
- Validate `amount > 0`.
- Append `DEPOSIT` transaction.
- Return transaction.

---

#### Withdraw

```python
def withdraw(
    self,
    account_id: str,
    amount: Decimal | int | float | str,
    timestamp: datetime | None = None,
) -> Transaction:
    ...
```

Behavior:

- Validate account exists.
- Validate `amount > 0`.
- Calculate current cash balance as of `timestamp`.
- Reject if withdrawal would make cash balance negative.
- Append `WITHDRAW` transaction.
- Return transaction.

Raises:

- `InvalidAmountError`
- `InsufficientFundsError`

---

### 3.9 Trade Methods

#### Buy Shares

```python
def buy(
    self,
    account_id: str,
    symbol: str,
    quantity: int,
    timestamp: datetime | None = None,
) -> Transaction:
    ...
```

Behavior:

- Validate account exists.
- Normalize symbol to uppercase.
- Validate symbol is supported.
- Validate `quantity > 0`.
- Fetch current share price using `get_share_price(symbol)`.
- Calculate total cost.
- Validate cash balance is sufficient.
- Append `BUY` transaction.
- Return transaction.

Raises:

- `InvalidQuantityError`
- `UnsupportedSymbolError`
- `InsufficientFundsError`

---

#### Sell Shares

```python
def sell(
    self,
    account_id: str,
    symbol: str,
    quantity: int,
    timestamp: datetime | None = None,
) -> Transaction:
    ...
```

Behavior:

- Validate account exists.
- Normalize symbol to uppercase.
- Validate symbol is supported.
- Validate `quantity > 0`.
- Calculate holdings as of `timestamp`.
- Reject if user does not own enough shares.
- Fetch current share price.
- Append `SELL` transaction.
- Return transaction.

Raises:

- `InvalidQuantityError`
- `UnsupportedSymbolError`
- `InsufficientSharesError`

---

### 3.10 Reporting Methods

#### Get Transactions

```python
def get_transactions(
    self,
    account_id: str,
    as_of: datetime | None = None,
) -> list[Transaction]:
    ...
```

Behavior:

- Return transactions for account.
- If `as_of` is provided, only return transactions where `transaction.timestamp <= as_of`.
- Return sorted by timestamp, then transaction ID.

---

#### Get Cash Balance

```python
def get_cash_balance(
    self,
    account_id: str,
    as_of: datetime | None = None,
) -> Decimal:
    ...
```

Calculation:

- `CREATE_ACCOUNT`: add amount.
- `DEPOSIT`: add amount.
- `WITHDRAW`: subtract amount.
- `BUY`: subtract total value.
- `SELL`: add total value.

---

#### Get Holdings Quantities

```python
def get_holding_quantities(
    self,
    account_id: str,
    as_of: datetime | None = None,
) -> dict[str, int]:
    ...
```

Calculation:

- `BUY`: add quantity.
- `SELL`: subtract quantity.
- Exclude symbols where final quantity is `0`.

---

#### Get Holdings Report

```python
def get_holdings(
    self,
    account_id: str,
    as_of: datetime | None = None,
) -> list[Holding]:
    ...
```

Behavior:

- Use `get_holding_quantities`.
- For each symbol, call `get_share_price(symbol)`.
- Calculate market value as `quantity * current_price`.
- Return holdings sorted by symbol.

Note:

- Historical reports use current prices because only current fixed test prices are available.
- Transaction prices are still stored for auditability.

---

#### Get Net Contributions

```python
def get_net_contributions(
    self,
    account_id: str,
    as_of: datetime | None = None,
) -> Decimal:
    ...
```

Calculation:

- `CREATE_ACCOUNT`: add amount.
- `DEPOSIT`: add amount.
- `WITHDRAW`: subtract amount.
- Ignore buys and sells.

---

#### Get Portfolio Value

```python
def get_portfolio_value(
    self,
    account_id: str,
    as_of: datetime | None = None,
) -> Decimal:
    ...
```

Calculation:

```text
cash_balance + current market value of holdings
```

---

#### Get Profit/Loss

```python
def get_profit_loss(
    self,
    account_id: str,
    as_of: datetime | None = None,
) -> Decimal:
    ...
```

Calculation:

```text
portfolio_value - net_contributions
```

This is the recommended P/L figure because it accounts for deposits and withdrawals.

---

#### Get Profit/Loss vs Initial Deposit

```python
def get_profit_loss_vs_initial_deposit(
    self,
    account_id: str,
    as_of: datetime | None = None,
) -> Decimal:
    ...
```

Calculation:

```text
portfolio_value - initial_deposit
```

This supports the explicit requirement to show profit/loss from the initial deposit.

---

#### Get Full Portfolio Report

```python
def get_portfolio_report(
    self,
    account_id: str,
    as_of: datetime | None = None,
) -> PortfolioReport:
    ...
```

Behavior:

- Return a full snapshot containing:
  - Cash balance.
  - Holdings.
  - Holdings value.
  - Total portfolio value.
  - Net contributions.
  - Initial deposit.
  - Profit/loss.
  - Profit/loss vs initial deposit.

---

### 3.11 Helper Functions

#### Normalize Decimal

```python
def to_decimal(value: Decimal | int | float | str) -> Decimal:
    ...
```

Behavior:

- Convert supported numeric input into `Decimal`.
- Convert floats using `str(value)` to avoid binary float artifacts.
- Quantize money values to two decimal places.
- Raise `InvalidAmountError` for invalid inputs.

---

#### Normalize Symbol

```python
def normalize_symbol(symbol: str) -> str:
    ...
```

Behavior:

- Strip whitespace.
- Uppercase.
- Reject empty symbols.

---

#### Transaction ID Generator

```python
def make_transaction_id() -> str:
    ...
```

Behavior:

- Return a unique string transaction ID.
- Use standard library `uuid.uuid4`.

---

#### Timestamp Helper

```python
def resolve_timestamp(timestamp: datetime | None) -> datetime:
    ...
```

Behavior:

- If `timestamp` is provided, return it.
- Otherwise return `datetime.now(timezone.utc)`.

---

#### Formatting Helpers for Frontend

These are optional but recommended to keep `app.py` simple.

```python
def decimal_to_display(value: Decimal) -> str:
    ...
```

```python
def transaction_to_row(transaction: Transaction) -> list[str | int | None]:
    ...
```

```python
def holding_to_row(holding: Holding) -> list[str | int]:
    ...
```

```python
def portfolio_report_to_summary(report: PortfolioReport) -> str:
    ...
```

---

## 4. Frontend Design: `app.py`

The frontend engineer will build a Gradio 6 app using `gr.Blocks`.

### 4.1 Important Gradio 6 API Guidance

Use:

```python
import gradio as gr
```

Basic app shape:

```python
with gr.Blocks(title="Trading Simulation Account Manager") as demo:
    ...
demo.launch()
```

Event listener pattern:

```python
button.click(
    fn=handler_function,
    inputs=[input_component_1, input_component_2],
    outputs=[output_component_1, output_component_2],
)
```

For a single input or output, both forms are acceptable:

```python
inputs=component
outputs=component
```

or:

```python
inputs=[component]
outputs=[component]
```

Prefer lists for consistency.

Use `gr.State` if storing Python objects in the UI state. However, because the backend service can be module-level in this simple app, state is optional.

Dynamic component updates in Gradio 6:

- Do **not** use old `gr.update(...)` patterns unless confirmed available.
- Prefer returning a new component instance to update component properties, for example:

```python
return gr.Dropdown(choices=new_choices, value=selected_value, interactive=True)
```

Data display:

- Use `gr.Dataframe`, not pandas.
- Since pandas is not available, provide plain list-of-lists as values.
- Configure headers directly on `gr.Dataframe`.

Recommended `gr.Dataframe` usage:

```python
gr.Dataframe(
    headers=["Symbol", "Quantity", "Current Price", "Market Value"],
    datatype=["str", "number", "str", "str"],
    label="Holdings",
    interactive=False,
)
```

Recommended components:

```python
gr.Textbox(label="Account ID")
gr.Number(label="Initial Deposit", precision=2)
gr.Dropdown(choices=["AAPL", "TSLA", "GOOGL"], label="Symbol")
gr.Number(label="Quantity", precision=0)
gr.Button("Create Account")
gr.Markdown()
gr.Dataframe()
```

Notes:

- `gr.Number` returns `int` or `float`; backend must validate and convert.
- Use `precision=0` for integer quantity inputs.
- Use `interactive=False` for output-only tables.
- Use `gr.Markdown` for status messages and portfolio summary.
- Use `demo.launch()` at the bottom.
- `demo.queue().launch()` is optional but not required.

---

### 4.2 Module-Level Service

At the top of `app.py`:

```python
service: TradingService
```

Initialize one global service instance:

```python
service = TradingService()
```

This gives the app shared in-memory state while running.

---

### 4.3 UI Layout

Suggested layout:

```text
# Trading Simulation Account Manager

Account Management
- Account ID textbox
- Initial Deposit number
- Create Account button
- Refresh Accounts button
- Account dropdown

Cash Operations
- Deposit amount
- Deposit button
- Withdraw amount
- Withdraw button

Trading
- Symbol dropdown
- Quantity number
- Buy button
- Sell button

Reports
- Refresh Report button
- Portfolio summary markdown
- Holdings dataframe
- Transactions dataframe
- Status markdown
```

---

### 4.4 Frontend Handler Functions

All handler functions should catch `TradingSimulationError` and general `Exception`, returning user-friendly messages.

#### Create Account Handler

```python
def handle_create_account(
    account_id: str,
    initial_deposit: float,
) -> tuple[gr.Dropdown, str, str, list[list[object]], list[list[object]]]:
    ...
```

Outputs:

1. Updated account dropdown.
2. Status markdown.
3. Portfolio summary markdown.
4. Holdings table rows.
5. Transactions table rows.

Behavior:

- Call `service.create_account`.
- Refresh account dropdown choices.
- Select the newly created account.
- Refresh report tables.

---

#### Refresh Accounts Handler

```python
def handle_refresh_accounts() -> gr.Dropdown:
    ...
```

Output:

- Updated account dropdown.

Behavior:

- Use `service.list_accounts()`.
- Return a new `gr.Dropdown(...)` with updated choices.

---

#### Deposit Handler

```python
def handle_deposit(
    account_id: str,
    amount: float,
) -> tuple[str, str, list[list[object]], list[list[object]]]:
    ...
```

Outputs:

1. Status markdown.
2. Portfolio summary markdown.
3. Holdings rows.
4. Transaction rows.

---

#### Withdraw Handler

```python
def handle_withdraw(
    account_id: str,
    amount: float,
) -> tuple[str, str, list[list[object]], list[list[object]]]:
    ...
```

Outputs:

1. Status markdown.
2. Portfolio summary markdown.
3. Holdings rows.
4. Transaction rows.

---

#### Buy Handler

```python
def handle_buy(
    account_id: str,
    symbol: str,
    quantity: float,
) -> tuple[str, str, list[list[object]], list[list[object]]]:
    ...
```

Outputs:

1. Status markdown.
2. Portfolio summary markdown.
3. Holdings rows.
4. Transaction rows.

Behavior:

- Convert `quantity` to integer before calling backend.
- Backend must still validate.

---

#### Sell Handler

```python
def handle_sell(
    account_id: str,
    symbol: str,
    quantity: float,
) -> tuple[str, str, list[list[object]], list[list[object]]]:
    ...
```

Outputs:

1. Status markdown.
2. Portfolio summary markdown.
3. Holdings rows.
4. Transaction rows.

---

#### Refresh Report Handler

```python
def handle_refresh_report(
    account_id: str,
) -> tuple[str, list[list[object]], list[list[object]], str]:
    ...
```

Outputs:

1. Portfolio summary markdown.
2. Holdings rows.
3. Transaction rows.
4. Status markdown.

---

### 4.5 Frontend Formatting Functions

These can live in `app.py` and call backend report methods.

#### Build Account Dropdown

```python
def build_account_dropdown(
    selected_account_id: str | None = None,
) -> gr.Dropdown:
    ...
```

Behavior:

- Get account IDs from service.
- Return:

```python
gr.Dropdown(
    choices=account_ids,
    value=selected_account_id,
    label="Account",
    interactive=True,
)
```

---

#### Build Empty Holdings Rows

```python
def empty_holdings_rows() -> list[list[object]]:
    ...
```

---

#### Build Empty Transaction Rows

```python
def empty_transaction_rows() -> list[list[object]]:
    ...
```

---

#### Build Holdings Rows

```python
def build_holdings_rows(account_id: str) -> list[list[object]]:
    ...
```

Expected row format:

```text
[
  symbol,
  quantity,
  current_price,
  market_value
]
```

---

#### Build Transaction Rows

```python
def build_transaction_rows(account_id: str) -> list[list[object]]:
    ...
```

Expected row format:

```text
[
  timestamp,
  transaction_type,
  symbol,
  quantity,
  share_price,
  amount,
  total_value
]
```

---

#### Build Portfolio Summary

```python
def build_portfolio_summary(account_id: str) -> str:
    ...
```

Suggested Markdown format:

```markdown
### Portfolio Summary

- Cash Balance: $...
- Holdings Value: $...
- Total Portfolio Value: $...
- Net Contributions: $...
- Initial Deposit: $...
- Profit/Loss: $...
- Profit/Loss vs Initial Deposit: $...
```

---

#### Build Full Report Output

```python
def build_report_outputs(
    account_id: str,
) -> tuple[str, list[list[object]], list[list[object]]]:
    ...
```

Returns:

1. Portfolio summary markdown.
2. Holdings rows.
3. Transaction rows.

---

### 4.6 Gradio Components

The frontend engineer should define these components inside `with gr.Blocks(...)`.

#### Account Components

```python
account_id_input = gr.Textbox(label="New Account ID", placeholder="e.g. alice")
initial_deposit_input = gr.Number(label="Initial Deposit", precision=2, value=10000)
create_account_button = gr.Button("Create Account")
refresh_accounts_button = gr.Button("Refresh Accounts")
account_dropdown = gr.Dropdown(choices=[], label="Account", interactive=True)
```

#### Cash Components

```python
deposit_amount_input = gr.Number(label="Deposit Amount", precision=2, value=1000)
deposit_button = gr.Button("Deposit")
withdraw_amount_input = gr.Number(label="Withdraw Amount", precision=2, value=100)
withdraw_button = gr.Button("Withdraw")
```

#### Trade Components

```python
symbol_dropdown = gr.Dropdown(
    choices=["AAPL", "TSLA", "GOOGL"],
    value="AAPL",
    label="Symbol",
    interactive=True,
)
quantity_input = gr.Number(label="Quantity", precision=0, value=1)
buy_button = gr.Button("Buy")
sell_button = gr.Button("Sell")
```

#### Report Components

```python
refresh_report_button = gr.Button("Refresh Report")
status_markdown = gr.Markdown()
portfolio_summary_markdown = gr.Markdown()
holdings_dataframe = gr.Dataframe(
    headers=["Symbol", "Quantity", "Current Price", "Market Value"],
    datatype=["str", "number", "str", "str"],
    label="Holdings",
    interactive=False,
)
transactions_dataframe = gr.Dataframe(
    headers=[
        "Timestamp",
        "Type",
        "Symbol",
        "Quantity",
        "Share Price",
        "Amount",
        "Total Value",
    ],
    datatype=["str", "str", "str", "number", "str", "str", "str"],
    label="Transactions",
    interactive=False,
)
```

---

### 4.7 Gradio Event Wiring

#### Create Account

```python
create_account_button.click(
    fn=handle_create_account,
    inputs=[account_id_input, initial_deposit_input],
    outputs=[
        account_dropdown,
        status_markdown,
        portfolio_summary_markdown,
        holdings_dataframe,
        transactions_dataframe,
    ],
)
```

#### Refresh Accounts

```python
refresh_accounts_button.click(
    fn=handle_refresh_accounts,
    inputs=[],
    outputs=[account_dropdown],
)
```

#### Deposit

```python
deposit_button.click(
    fn=handle_deposit,
    inputs=[account_dropdown, deposit_amount_input],
    outputs=[
        status_markdown,
        portfolio_summary_markdown,
        holdings_dataframe,
        transactions_dataframe,
    ],
)
```

#### Withdraw

```python
withdraw_button.click(
    fn=handle_withdraw,
    inputs=[account_dropdown, withdraw_amount_input],
    outputs=[
        status_markdown,
        portfolio_summary_markdown,
        holdings_dataframe,
        transactions_dataframe,
    ],
)
```

#### Buy

```python
buy_button.click(
    fn=handle_buy,
    inputs=[account_dropdown, symbol_dropdown, quantity_input],
    outputs=[
        status_markdown,
        portfolio_summary_markdown,
        holdings_dataframe,
        transactions_dataframe,
    ],
)
```

#### Sell

```python
sell_button.click(
    fn=handle_sell,
    inputs=[account_dropdown, symbol_dropdown, quantity_input],
    outputs=[
        status_markdown,
        portfolio_summary_markdown,
        holdings_dataframe,
        transactions_dataframe,
    ],
)
```

#### Refresh Report

```python
refresh_report_button.click(
    fn=handle_refresh_report,
    inputs=[account_dropdown],
    outputs=[
        portfolio_summary_markdown,
        holdings_dataframe,
        transactions_dataframe,
        status_markdown,
    ],
)
```

---

## 5. Unit Test Design: `test_backend.py`

Use standard library `unittest`.

```python
import unittest
```

Tests should import from `backend.py`.

---

### 5.1 Test Class

```python
class TradingServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        ...
```

`setUp` should create a fresh `TradingService` for every test.

---

### 5.2 Required Test Cases

#### Price Function

```python
def test_get_share_price_supported_symbols(self) -> None:
    ...
```

Verify:

- `AAPL == Decimal("150.00")`
- `TSLA == Decimal("250.00")`
- `GOOGL == Decimal("2800.00")`

```python
def test_get_share_price_rejects_unsupported_symbol(self) -> None:
    ...
```

---

#### Account Creation

```python
def test_create_account_with_initial_deposit(self) -> None:
    ...
```

Verify:

- Account exists.
- Cash balance equals initial deposit.
- One transaction exists.
- Transaction type is `CREATE_ACCOUNT`.

```python
def test_create_account_rejects_duplicate_account_id(self) -> None:
    ...
```

```python
def test_create_account_rejects_non_positive_initial_deposit(self) -> None:
    ...
```

---

#### Deposits

```python
def test_deposit_increases_cash_balance(self) -> None:
    ...
```

```python
def test_deposit_rejects_non_positive_amount(self) -> None:
    ...
```

---

#### Withdrawals

```python
def test_withdraw_decreases_cash_balance(self) -> None:
    ...
```

```python
def test_withdraw_rejects_insufficient_funds(self) -> None:
    ...
```

```python
def test_withdraw_all_cash_is_allowed(self) -> None:
    ...
```

---

#### Buying

```python
def test_buy_shares_decreases_cash_and_increases_holdings(self) -> None:
    ...
```

Example:

- Create account with `1000`.
- Buy `2 AAPL`.
- Cost is `300`.
- Cash is `700`.
- Holdings are `{"AAPL": 2}`.

```python
def test_buy_rejects_insufficient_funds(self) -> None:
    ...
```

```python
def test_buy_rejects_invalid_quantity(self) -> None:
    ...
```

```python
def test_buy_rejects_unsupported_symbol(self) -> None:
    ...
```

---

#### Selling

```python
def test_sell_shares_increases_cash_and_decreases_holdings(self) -> None:
    ...
```

Example:

- Create account with `1000`.
- Buy `2 AAPL`.
- Sell `1 AAPL`.
- Cash should be `850`.
- Holdings should be `{"AAPL": 1}`.

```python
def test_sell_rejects_insufficient_shares(self) -> None:
    ...
```

```python
def test_sell_all_shares_removes_holding_from_report(self) -> None:
    ...
```

```python
def test_sell_rejects_invalid_quantity(self) -> None:
    ...
```

---

#### Portfolio Reporting

```python
def test_portfolio_value_includes_cash_and_holdings_value(self) -> None:
    ...
```

Example:

- Create account with `1000`.
- Buy `2 AAPL`.
- Cash = `700`.
- Holdings value = `300`.
- Portfolio value = `1000`.

```python
def test_profit_loss_uses_net_contributions(self) -> None:
    ...
```

Example:

- Create account with `1000`.
- Buy `2 AAPL`.
- Portfolio value remains `1000`.
- Profit/loss should be `0`.

```python
def test_profit_loss_vs_initial_deposit(self) -> None:
    ...
```

```python
def test_get_portfolio_report_contains_expected_values(self) -> None:
    ...
```

---

#### Transaction History

```python
def test_transactions_are_recorded_in_order(self) -> None:
    ...
```

Verify:

- Create account.
- Deposit.
- Buy.
- Sell.
- Withdraw.
- Transaction types appear in expected order.

---

#### Historical Reporting

Use explicit timestamps.

```python
def test_holdings_as_of_timestamp(self) -> None:
    ...
```

Example:

- `t1`: create account.
- `t2`: buy 2 AAPL.
- `t3`: sell 1 AAPL.
- Holdings as of `t2` should be 2 AAPL.
- Holdings as of `t3` should be 1 AAPL.

```python
def test_cash_balance_as_of_timestamp(self) -> None:
    ...
```

```python
def test_transactions_as_of_timestamp(self) -> None:
    ...
```

```python
def test_profit_loss_as_of_timestamp(self) -> None:
    ...
```

---

### 5.3 Test Runner

At bottom of `test_backend.py`:

```python
if __name__ == "__main__":
    unittest.main()
```

---

## 6. Engineer Assignments

## backend_engineer

Own file:

```text
backend.py
```

Responsibilities:

1. Implement all backend data classes:
   - `Transaction`
   - `Account`
   - `Holding`
   - `PortfolioReport`

2. Implement enum:
   - `TransactionType`

3. Implement exceptions:
   - `TradingSimulationError`
   - `AccountNotFoundError`
   - `DuplicateAccountError`
   - `InvalidAmountError`
   - `InvalidQuantityError`
   - `UnsupportedSymbolError`
   - `InsufficientFundsError`
   - `InsufficientSharesError`

4. Implement fixed price function:

```python
def get_share_price(symbol: str) -> Decimal:
    ...
```

5. Implement helper functions:

```python
def to_decimal(value: Decimal | int | float | str) -> Decimal:
    ...
```

```python
def normalize_symbol(symbol: str) -> str:
    ...
```

```python
def make_transaction_id() -> str:
    ...
```

```python
def resolve_timestamp(timestamp: datetime | None) -> datetime:
    ...
```

```python
def decimal_to_display(value: Decimal) -> str:
    ...
```

```python
def transaction_to_row(transaction: Transaction) -> list[str | int | None]:
    ...
```

```python
def holding_to_row(holding: Holding) -> list[str | int]:
    ...
```

```python
def portfolio_report_to_summary(report: PortfolioReport) -> str:
    ...
```

6. Implement `TradingService` with all public methods:

```python
class TradingService:
    def __init__(self) -> None:
        ...

    def create_account(
        self,
        account_id: str,
        initial_deposit: Decimal | int | float | str,
        timestamp: datetime | None = None,
    ) -> Account:
        ...

    def get_account(self, account_id: str) -> Account:
        ...

    def list_accounts(self) -> list[str]:
        ...

    def deposit(
        self,
        account_id: str,
        amount: Decimal | int | float | str,
        timestamp: datetime | None = None,
    ) -> Transaction:
        ...

    def withdraw(
        self,
        account_id: str,
        amount: Decimal | int | float | str,
        timestamp: datetime | None = None,
    ) -> Transaction:
        ...

    def buy(
        self,
        account_id: str,
        symbol: str,
        quantity: int,
        timestamp: datetime | None = None,
    ) -> Transaction:
        ...

    def sell(
        self,
        account_id: str,
        symbol: str,
        quantity: int,
        timestamp: datetime | None = None,
    ) -> Transaction:
        ...

    def get_transactions(
        self,
        account_id: str,
        as_of: datetime | None = None,
    ) -> list[Transaction]:
        ...

    def get_cash_balance(
        self,
        account_id: str,
        as_of: datetime | None = None,
    ) -> Decimal:
        ...

    def get_holding_quantities(
        self,
        account_id: str,
        as_of: datetime | None = None,
    ) -> dict[str, int]:
        ...

    def get_holdings(
        self,
        account_id: str,
        as_of: datetime | None = None,
    ) -> list[Holding]:
        ...

    def get_net_contributions(
        self,
        account_id: str,
        as_of: datetime | None = None,
    ) -> Decimal:
        ...

    def get_portfolio_value(
        self,
        account_id: str,
        as_of: datetime | None = None,
    ) -> Decimal:
        ...

    def get_profit_loss(
        self,
        account_id: str,
        as_of: datetime | None = None,
    ) -> Decimal:
        ...

    def get_profit_loss_vs_initial_deposit(
        self,
        account_id: str,
        as_of: datetime | None = None,
    ) -> Decimal:
        ...

    def get_portfolio_report(
        self,
        account_id: str,
        as_of: datetime | None = None,
    ) -> PortfolioReport:
        ...
```

Implementation notes:

- Use `Decimal` for money.
- Quantize money to two decimal places.
- Normalize symbols to uppercase.
- Do not allow negative or zero amounts.
- Do not allow negative or zero share quantities.
- Do not mutate transaction objects after creation.
- Keep account balances derived from transaction history.

---

## frontend_engineer

Own file:

```text
app.py
```

Responsibilities:

1. Import backend service and exceptions.
2. Create one module-level `TradingService`.
3. Build Gradio 6 app using `gr.Blocks`.
4. Implement frontend handlers:
   - `handle_create_account`
   - `handle_refresh_accounts`
   - `handle_deposit`
   - `handle_withdraw`
   - `handle_buy`
   - `handle_sell`
   - `handle_refresh_report`
5. Implement frontend formatting helpers:
   - `build_account_dropdown`
   - `empty_holdings_rows`
   - `empty_transaction_rows`
   - `build_holdings_rows`
   - `build_transaction_rows`
   - `build_portfolio_summary`
   - `build_report_outputs`
6. Wire all Gradio events using `.click(...)`.
7. Launch app with:

```python
demo.launch()
```

Important Gradio 6 reminders:

- Use `gr.Blocks`, `gr.Row`, `gr.Column`, `gr.Markdown`, `gr.Textbox`, `gr.Number`, `gr.Dropdown`, `gr.Button`, and `gr.Dataframe`.
- Event listener signature:

```python
component.click(fn=..., inputs=[...], outputs=[...])
```

- To update dropdown choices, return a new dropdown component:

```python
gr.Dropdown(choices=account_ids, value=selected_id, label="Account", interactive=True)
```

- Use list-of-lists for `gr.Dataframe` values.
- Do not rely on pandas.
- Catch backend domain exceptions and display readable errors in `status_markdown`.

---

## test_engineer

Own file:

```text
test_backend.py
```

Responsibilities:

1. Write backend-only unit tests using `unittest`.
2. Do not test Gradio UI.
3. Cover:
   - Price lookup.
   - Account creation.
   - Deposits.
   - Withdrawals.
   - Buys.
   - Sells.
   - Invalid operation prevention.
   - Portfolio value.
   - Profit/loss.
   - Holdings reports.
   - Historical `as_of` reports.
   - Transaction history.

Required imports should come from `backend.py`.

Test runner:

```python
if __name__ == "__main__":
    unittest.main()
```

---

## 7. Acceptance Criteria

The system is complete when:

1. `backend.py` supports all required account, cash, trade, and reporting operations.
2. Invalid operations are rejected with clear domain exceptions.
3. `app.py` launches a working Gradio UI.
4. Users can:
   - Create accounts.
   - Deposit funds.
   - Withdraw funds.
   - Buy shares.
   - Sell shares.
   - View holdings.
   - View portfolio value.
   - View profit/loss.
   - View transactions.
5. `test_backend.py` passes with:

```bash
uv run python test_backend.py
```

6. The Gradio app runs with:

```bash
uv run python app.py
```