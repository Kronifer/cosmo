from dataclasses import dataclass


@dataclass
class SSL:
    """Container class for an SSL certificate."""

    cert_path: str
    key_path: str
