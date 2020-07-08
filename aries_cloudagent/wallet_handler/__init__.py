"""Wallet handler  -  enables aca-py to handle more than one wallet with the same agent."""
from .setup import setup
from .handler import WalletHandler
setup = setup
WalletHanlder = WalletHandler
