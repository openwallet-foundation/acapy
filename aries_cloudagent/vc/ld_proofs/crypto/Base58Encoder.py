import base58


class Base58Encoder(object):
  @staticmethod
  def encode(data):
    return base58.b58encode(data)

  @staticmethod
  def decode(data):
    return base58.b58decode(data)
