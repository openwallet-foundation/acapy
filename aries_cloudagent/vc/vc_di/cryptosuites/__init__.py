from .eddsa_jcs_2022 import EddsaJcs2022

CONTEXTS = {
    'data-integrity-v2': 'https://w3id.org/security/data-integrity/v2'
}

CRYPTOSUITES = {
    "eddsa-jcs-2022": EddsaJcs2022,
}

__all__ = [
    "EddsaJcs2022",
]