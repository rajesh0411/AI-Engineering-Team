import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from backend import (
    AccountNotFoundError,
    DuplicateAccountError,
    InsufficientFundsError,
    InsufficientSharesError,
    InvalidAmountError,
    InvalidQuantityError,
    PortfolioReport,
    TradingService,
    TransactionType,
    UnsupportedSymbolError,
    get_share_price,
)


class TradingServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = TradingService()
        self.base = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    def ts(self, minutes: int) -> datetime:
        return self.base + timedelta(minutes=minutes)

    def test_get_share_price_supported_symbols(self) -> None:
        self.assertEqual(get_share_price("AAPL"), Decimal("150.00"))
        self.assertEqual(get_share_price("TSLA"), Decimal("250.00"))
        self.assertEqual(get_share_price("GOOGL"), Decimal("2800.00"))

    def test_get_share_price_rejects_unsupported_symbol(self) -> None:
        with self.assertRaises(UnsupportedSymbolError):
            get_share_price("MSFT")

    def test_create_account_with_initial_deposit(self) -> None:
        account = self.service.create_account("alice", 1000)
        self.assertEqual(account.account_id, "alice")
        self.assertEqual(self.service.get_cash_balance("alice"), Decimal("1000.00"))
        self.assertEqual(len(account.transactions), 1)
        self.assertEqual(account.transactions[0].transaction_type, TransactionType.CREATE_ACCOUNT)

    def test_create_account_rejects_duplicate_account_id(self) -> None:
        self.service.create_account("alice", 1000)
        with self.assertRaises(DuplicateAccountError):
            self.service.create_account("alice", 500)

    def test_create_account_rejects_non_positive_initial_deposit(self) -> None:
        with self.assertRaises(InvalidAmountError):
            self.service.create_account("alice", 0)

    def test_deposit_increases_cash_balance(self) -> None:
        self.service.create_account("alice", 1000)
        self.service.deposit("alice", 250)
        self.assertEqual(self.service.get_cash_balance("alice"), Decimal("1250.00"))

    def test_deposit_rejects_non_positive_amount(self) -> None:
        self.service.create_account("alice", 1000)
        with self.assertRaises(InvalidAmountError):
            self.service.deposit("alice", 0)

    def test_withdraw_decreases_cash_balance(self) -> None:
        self.service.create_account("alice", 1000)
        self.service.withdraw("alice", 250)
        self.assertEqual(self.service.get_cash_balance("alice"), Decimal("750.00"))

    def test_withdraw_rejects_insufficient_funds(self) -> None:
        self.service.create_account("alice", 100)
        with self.assertRaises(InsufficientFundsError):
            self.service.withdraw("alice", 150)

    def test_withdraw_all_cash_is_allowed(self) -> None:
        self.service.create_account("alice", 100)
        self.service.withdraw("alice", 100)
        self.assertEqual(self.service.get_cash_balance("alice"), Decimal("0.00"))

    def test_buy_shares_decreases_cash_and_increases_holdings(self) -> None:
        self.service.create_account("alice", 1000)
        self.service.buy("alice", "AAPL", 2)
        self.assertEqual(self.service.get_cash_balance("alice"), Decimal("700.00"))
        self.assertEqual(self.service.get_holding_quantities("alice"), {"AAPL": 2})

    def test_buy_rejects_insufficient_funds(self) -> None:
        self.service.create_account("alice", 100)
        with self.assertRaises(InsufficientFundsError):
            self.service.buy("alice", "AAPL", 1)

    def test_buy_rejects_invalid_quantity(self) -> None:
        self.service.create_account("alice", 1000)
        with self.assertRaises(InvalidQuantityError):
            self.service.buy("alice", "AAPL", 0)

    def test_buy_rejects_unsupported_symbol(self) -> None:
        self.service.create_account("alice", 1000)
        with self.assertRaises(UnsupportedSymbolError):
            self.service.buy("alice", "MSFT", 1)

    def test_sell_shares_increases_cash_and_decreases_holdings(self) -> None:
        self.service.create_account("alice", 1000)
        self.service.buy("alice", "AAPL", 2)
        self.service.sell("alice", "AAPL", 1)
        self.assertEqual(self.service.get_cash_balance("alice"), Decimal("850.00"))
        self.assertEqual(self.service.get_holding_quantities("alice"), {"AAPL": 1})

    def test_sell_rejects_insufficient_shares(self) -> None:
        self.service.create_account("alice", 1000)
        with self.assertRaises(InsufficientSharesError):
            self.service.sell("alice", "AAPL", 1)

    def test_sell_all_shares_removes_holding_from_report(self) -> None:
        self.service.create_account("alice", 1000)
        self.service.buy("alice", "AAPL", 2)
        self.service.sell("alice", "AAPL", 2)
        self.assertEqual(self.service.get_holding_quantities("alice"), {})
        self.assertEqual(self.service.get_holdings("alice"), [])

    def test_sell_rejects_invalid_quantity(self) -> None:
        self.service.create_account("alice", 1000)
        with self.assertRaises(InvalidQuantityError):
            self.service.sell("alice", "AAPL", 0)

    def test_portfolio_value_includes_cash_and_holdings_value(self) -> None:
        self.service.create_account("alice", 1000)
        self.service.buy("alice", "AAPL", 2)
        self.assertEqual(self.service.get_portfolio_value("alice"), Decimal("1000.00"))

    def test_profit_loss_uses_net_contributions(self) -> None:
        self.service.create_account("alice", 1000)
        self.service.buy("alice", "AAPL", 2)
        self.assertEqual(self.service.get_profit_loss("alice"), Decimal("0.00"))

    def test_profit_loss_vs_initial_deposit(self) -> None:
        self.service.create_account("alice", 1000)
        self.service.buy("alice", "AAPL", 2)
        self.assertEqual(self.service.get_profit_loss_vs_initial_deposit("alice"), Decimal("0.00"))

    def test_get_portfolio_report_contains_expected_values(self) -> None:
        self.service.create_account("alice", 1000)
        self.service.buy("alice", "AAPL", 2)
        report = self.service.get_portfolio_report("alice")
        self.assertIsInstance(report, PortfolioReport)
        self.assertEqual(report.cash_balance, Decimal("700.00"))
        self.assertEqual(report.holdings_value, Decimal("300.00"))
        self.assertEqual(report.total_value, Decimal("1000.00"))
        self.assertEqual(report.profit_loss, Decimal("0.00"))
        self.assertEqual(report.profit_loss_vs_initial_deposit, Decimal("0.00"))

    def test_transactions_are_recorded_in_order(self) -> None:
        self.service.create_account("alice", 1000, timestamp=self.ts(0))
        self.service.deposit("alice", 100, timestamp=self.ts(1))
        self.service.buy("alice", "AAPL", 1, timestamp=self.ts(2))
        self.service.sell("alice", "AAPL", 1, timestamp=self.ts(3))
        self.service.withdraw("alice", 50, timestamp=self.ts(4))
        tx_types = [t.transaction_type for t in self.service.get_transactions("alice")]
        self.assertEqual(tx_types, [TransactionType.CREATE_ACCOUNT, TransactionType.DEPOSIT, TransactionType.BUY, TransactionType.SELL, TransactionType.WITHDRAW])

    def test_holdings_as_of_timestamp(self) -> None:
        self.service.create_account("alice", 1000, timestamp=self.ts(0))
        self.service.buy("alice", "AAPL", 2, timestamp=self.ts(1))
        self.service.sell("alice", "AAPL", 1, timestamp=self.ts(2))
        self.assertEqual(self.service.get_holding_quantities("alice", as_of=self.ts(1)), {"AAPL": 2})
        self.assertEqual(self.service.get_holding_quantities("alice", as_of=self.ts(2)), {"AAPL": 1})

    def test_cash_balance_as_of_timestamp(self) -> None:
        self.service.create_account("alice", 1000, timestamp=self.ts(0))
        self.service.buy("alice", "AAPL", 2, timestamp=self.ts(1))
        self.service.withdraw("alice", 100, timestamp=self.ts(2))
        self.assertEqual(self.service.get_cash_balance("alice", as_of=self.ts(1)), Decimal("700.00"))
        self.assertEqual(self.service.get_cash_balance("alice", as_of=self.ts(2)), Decimal("600.00"))

    def test_transactions_as_of_timestamp(self) -> None:
        self.service.create_account("alice", 1000, timestamp=self.ts(0))
        self.service.deposit("alice", 100, timestamp=self.ts(1))
        self.service.buy("alice", "AAPL", 1, timestamp=self.ts(2))
        self.assertEqual(len(self.service.get_transactions("alice", as_of=self.ts(1))), 2)
        self.assertEqual(len(self.service.get_transactions("alice", as_of=self.ts(2))), 3)

    def test_profit_loss_as_of_timestamp(self) -> None:
        self.service.create_account("alice", 1000, timestamp=self.ts(0))
        self.service.deposit("alice", 100, timestamp=self.ts(1))
        self.service.buy("alice", "AAPL", 2, timestamp=self.ts(2))
        self.assertEqual(self.service.get_profit_loss("alice", as_of=self.ts(2)), Decimal("0.00"))


if __name__ == "__main__":
    unittest.main()
