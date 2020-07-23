"""Wallet handler enables aca-py to manage multiple wallets with the same agent."""
from .setup import setup
from .handler import WalletHandler
setup = setup
WalletHanlder = WalletHandler
