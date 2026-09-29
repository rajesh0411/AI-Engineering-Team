from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enum import Enum
from typing import Iterable
from uuid import uuid4

SUPPORTED_PRICES: dict[str, str] = {
    "AAPL": "150.00",
    "TSLA": "250.00",
    "GOOGL": "2800.00",
}

_MONEY_QUANT = Decimal("0.01")


class TransactionType(str, Enum):
    CREATE_ACCOUNT = "CREATE_ACCOUNT"
    DEPOSIT = "DEPOSIT"
    WITHDRAW = "WITHDRAW"
    BUY = "BUY"
    SELL = "SELL"


class TradingSimulationError(Exception):
    pass


class AccountNotFoundError(TradingSimulationError):
    pass


class DuplicateAccountError(TradingSimulationError):
    pass


class InvalidAmountError(TradingSimulationError):
    pass


class InvalidQuantityError(TradingSimulationError):
    pass


class UnsupportedSymbolError(TradingSimulationError):
    pass


class InsufficientFundsError(TradingSimulationError):
    pass


class InsufficientSharesError(TradingSimulationError):
    pass


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


@dataclass
class Account:
    account_id: str
    created_at: datetime
    initial_deposit: Decimal
    transactions: list[Transaction]


@dataclass(frozen=True)
class Holding:
    symbol: str
    quantity: int
    current_price: Decimal
    market_value: Decimal


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


def to_decimal(value: Decimal | int | float | str) -> Decimal:
    try:
        if isinstance(value, Decimal):
            dec = value
        elif isinstance(value, float):
            dec = Decimal(str(value))
        else:
            dec = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise InvalidAmountError("Invalid numeric value") from None
    return dec.quantize(_MONEY_QUANT, rounding=ROUND_HALF_UP)


def normalize_symbol(symbol: str) -> str:
    if symbol is None:
        raise UnsupportedSymbolError("Symbol is required")
    normalized = symbol.strip().upper()
    if not normalized:
        raise UnsupportedSymbolError("Symbol is required")
    return normalized


def make_transaction_id() -> str:
    return str(uuid4())


def resolve_timestamp(timestamp: datetime | None) -> datetime:
    return timestamp if timestamp is not None else datetime.now(timezone.utc)


def decimal_to_display(value: Decimal) -> str:
    return f"{value.quantize(_MONEY_QUANT, rounding=ROUND_HALF_UP):f}"


def transaction_to_row(transaction: Transaction) -> list[str | int | None]:
    return [
        transaction.timestamp.isoformat(),
        transaction.transaction_type.value,
        transaction.symbol,
        transaction.quantity,
        decimal_to_display(transaction.share_price) if transaction.share_price is not None else None,
        decimal_to_display(transaction.amount) if transaction.amount is not None else None,
        decimal_to_display(transaction.total_value) if transaction.total_value is not None else None,
    ]


def holding_to_row(holding: Holding) -> list[str | int]:
    return [
        holding.symbol,
        holding.quantity,
        decimal_to_display(holding.current_price),
        decimal_to_display(holding.market_value),
    ]


def portfolio_report_to_summary(report: PortfolioReport) -> str:
    return (
        "### Portfolio Summary\n\n"
        f"- Cash Balance: ${decimal_to_display(report.cash_balance)}\n"
        f"- Holdings Value: ${decimal_to_display(report.holdings_value)}\n"
        f"- Total Portfolio Value: ${decimal_to_display(report.total_value)}\n"
        f"- Net Contributions: ${decimal_to_display(report.net_contributions)}\n"
        f"- Initial Deposit: ${decimal_to_display(report.initial_deposit)}\n"
        f"- Profit/Loss: ${decimal_to_display(report.profit_loss)}\n"
        f"- Profit/Loss vs Initial Deposit: ${decimal_to_display(report.profit_loss_vs_initial_deposit)}"
    )


def get_share_price(symbol: str) -> Decimal:
    normalized = normalize_symbol(symbol)
    try:
        return Decimal(SUPPORTED_PRICES[normalized]).quantize(_MONEY_QUANT)
    except KeyError:
        raise UnsupportedSymbolError(f"Unsupported symbol: {symbol}") from None


class TradingService:
    def __init__(self) -> None:
        self._accounts: dict[str, Account] = {}

    def _get_account_or_raise(self, account_id: str) -> Account:
        try:
            return self._accounts[account_id]
        except KeyError:
            raise AccountNotFoundError(f"Account not found: {account_id}") from None

    def create_account(
        self,
        account_id: str,
        initial_deposit: Decimal | int | float | str,
        timestamp: datetime | None = None,
    ) -> Account:
        account_id = (account_id or "").strip()
        if not account_id:
            raise InvalidAmountError("Account ID is required")
        if account_id in self._accounts:
            raise DuplicateAccountError(f"Account already exists: {account_id}")
        deposit = to_decimal(initial_deposit)
        if deposit <= 0:
            raise InvalidAmountError("Initial deposit must be positive")
        ts = resolve_timestamp(timestamp)
        transaction = Transaction(
            transaction_id=make_transaction_id(),
            account_id=account_id,
            transaction_type=TransactionType.CREATE_ACCOUNT,
            timestamp=ts,
            amount=deposit,
        )
        account = Account(account_id=account_id, created_at=ts, initial_deposit=deposit, transactions=[transaction])
        self._accounts[account_id] = account
        return account

    def get_account(self, account_id: str) -> Account:
        return self._get_account_or_raise(account_id)

    def list_accounts(self) -> list[str]:
        return sorted(self._accounts)

    def deposit(
        self,
        account_id: str,
        amount: Decimal | int | float | str,
        timestamp: datetime | None = None,
    ) -> Transaction:
        account = self._get_account_or_raise(account_id)
        amt = to_decimal(amount)
        if amt <= 0:
            raise InvalidAmountError("Deposit amount must be positive")
        tx = Transaction(make_transaction_id(), account.account_id, TransactionType.DEPOSIT, resolve_timestamp(timestamp), amount=amt)
        account.transactions.append(tx)
        return tx

    def withdraw(
        self,
        account_id: str,
        amount: Decimal | int | float | str,
        timestamp: datetime | None = None,
    ) -> Transaction:
        account = self._get_account_or_raise(account_id)
        amt = to_decimal(amount)
        if amt <= 0:
            raise InvalidAmountError("Withdrawal amount must be positive")
        as_of = resolve_timestamp(timestamp)
        if self.get_cash_balance(account_id, as_of=as_of) < amt:
            raise InsufficientFundsError("Insufficient funds")
        tx = Transaction(make_transaction_id(), account.account_id, TransactionType.WITHDRAW, as_of, amount=amt)
        account.transactions.append(tx)
        return tx

    def buy(
        self,
        account_id: str,
        symbol: str,
        quantity: int,
        timestamp: datetime | None = None,
    ) -> Transaction:
        account = self._get_account_or_raise(account_id)
        symbol = normalize_symbol(symbol)
        if quantity <= 0:
            raise InvalidQuantityError("Quantity must be positive")
        price = get_share_price(symbol)
        total_value = (price * Decimal(quantity)).quantize(_MONEY_QUANT)
        as_of = resolve_timestamp(timestamp)
        if self.get_cash_balance(account_id, as_of=as_of) < total_value:
            raise InsufficientFundsError("Insufficient funds")
        tx = Transaction(make_transaction_id(), account.account_id, TransactionType.BUY, as_of, symbol=symbol, quantity=quantity, share_price=price, total_value=total_value)
        account.transactions.append(tx)
        return tx

    def sell(
        self,
        account_id: str,
        symbol: str,
        quantity: int,
        timestamp: datetime | None = None,
    ) -> Transaction:
        account = self._get_account_or_raise(account_id)
        symbol = normalize_symbol(symbol)
        if quantity <= 0:
            raise InvalidQuantityError("Quantity must be positive")
        holdings = self.get_holding_quantities(account_id, as_of=resolve_timestamp(timestamp))
        if holdings.get(symbol, 0) < quantity:
            raise InsufficientSharesError("Insufficient shares")
        price = get_share_price(symbol)
        total_value = (price * Decimal(quantity)).quantize(_MONEY_QUANT)
        as_of = resolve_timestamp(timestamp)
        tx = Transaction(make_transaction_id(), account.account_id, TransactionType.SELL, as_of, symbol=symbol, quantity=quantity, share_price=price, total_value=total_value)
        account.transactions.append(tx)
        return tx

    def _iter_transactions(self, account_id: str, as_of: datetime | None = None) -> Iterable[Transaction]:
        account = self._get_account_or_raise(account_id)
        txs = account.transactions
        if as_of is not None:
            txs = [tx for tx in txs if tx.timestamp <= as_of]
        return sorted(txs, key=lambda tx: (tx.timestamp, tx.transaction_id))

    def get_transactions(self, account_id: str, as_of: datetime | None = None) -> list[Transaction]:
        return list(self._iter_transactions(account_id, as_of=as_of))

    def get_cash_balance(self, account_id: str, as_of: datetime | None = None) -> Decimal:
        balance = Decimal("0.00")
        for tx in self._iter_transactions(account_id, as_of=as_of):
            if tx.transaction_type in {TransactionType.CREATE_ACCOUNT, TransactionType.DEPOSIT}:
                balance += tx.amount or Decimal("0.00")
            elif tx.transaction_type in {TransactionType.WITHDRAW}:
                balance -= tx.amount or Decimal("0.00")
            elif tx.transaction_type == TransactionType.BUY:
                balance -= tx.total_value or Decimal("0.00")
            elif tx.transaction_type == TransactionType.SELL:
                balance += tx.total_value or Decimal("0.00")
        return balance.quantize(_MONEY_QUANT)

    def get_holding_quantities(self, account_id: str, as_of: datetime | None = None) -> dict[str, int]:
        quantities: dict[str, int] = {}
        for tx in self._iter_transactions(account_id, as_of=as_of):
            if tx.transaction_type == TransactionType.BUY and tx.symbol:
                quantities[tx.symbol] = quantities.get(tx.symbol, 0) + (tx.quantity or 0)
            elif tx.transaction_type == TransactionType.SELL and tx.symbol:
                quantities[tx.symbol] = quantities.get(tx.symbol, 0) - (tx.quantity or 0)
        return {symbol: qty for symbol, qty in quantities.items() if qty != 0}

    def get_holdings(self, account_id: str, as_of: datetime | None = None) -> list[Holding]:
        holdings = []
        for symbol, quantity in sorted(self.get_holding_quantities(account_id, as_of=as_of).items()):
            current_price = get_share_price(symbol)
            market_value = (current_price * Decimal(quantity)).quantize(_MONEY_QUANT)
            holdings.append(Holding(symbol=symbol, quantity=quantity, current_price=current_price, market_value=market_value))
        return holdings

    def get_net_contributions(self, account_id: str, as_of: datetime | None = None) -> Decimal:
        total = Decimal("0.00")
        for tx in self._iter_transactions(account_id, as_of=as_of):
            if tx.transaction_type in {TransactionType.CREATE_ACCOUNT, TransactionType.DEPOSIT}:
                total += tx.amount or Decimal("0.00")
            elif tx.transaction_type == TransactionType.WITHDRAW:
                total -= tx.amount or Decimal("0.00")
        return total.quantize(_MONEY_QUANT)

    def get_portfolio_value(self, account_id: str, as_of: datetime | None = None) -> Decimal:
        cash = self.get_cash_balance(account_id, as_of=as_of)
        holdings_value = sum((holding.market_value for holding in self.get_holdings(account_id, as_of=as_of)), Decimal("0.00"))
        return (cash + holdings_value).quantize(_MONEY_QUANT)

    def get_profit_loss(self, account_id: str, as_of: datetime | None = None) -> Decimal:
        return (self.get_portfolio_value(account_id, as_of=as_of) - self.get_net_contributions(account_id, as_of=as_of)).quantize(_MONEY_QUANT)

    def get_profit_loss_vs_initial_deposit(self, account_id: str, as_of: datetime | None = None) -> Decimal:
        account = self._get_account_or_raise(account_id)
        return (self.get_portfolio_value(account_id, as_of=as_of) - account.initial_deposit).quantize(_MONEY_QUANT)

    def get_portfolio_report(self, account_id: str, as_of: datetime | None = None) -> PortfolioReport:
        account = self._get_account_or_raise(account_id)
        cash = self.get_cash_balance(account_id, as_of=as_of)
        holdings = self.get_holdings(account_id, as_of=as_of)
        holdings_value = sum((h.market_value for h in holdings), Decimal("0.00")).quantize(_MONEY_QUANT)
        total_value = (cash + holdings_value).quantize(_MONEY_QUANT)
        net_contributions = self.get_net_contributions(account_id, as_of=as_of)
        profit_loss = (total_value - net_contributions).quantize(_MONEY_QUANT)
        profit_loss_vs_initial_deposit = (total_value - account.initial_deposit).quantize(_MONEY_QUANT)
        return PortfolioReport(
            account_id=account_id,
            as_of=resolve_timestamp(as_of),
            cash_balance=cash,
            holdings=holdings,
            holdings_value=holdings_value,
            total_value=total_value,
            net_contributions=net_contributions,
            initial_deposit=account.initial_deposit,
            profit_loss=profit_loss,
            profit_loss_vs_initial_deposit=profit_loss_vs_initial_deposit,
        )
