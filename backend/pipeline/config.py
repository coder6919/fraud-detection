from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = PROJECT_ROOT / "ieee-fraud-detection"
GRAPH_STORE_DIR = BACKEND_DIR / "graph_store"

# Fields that compose the account fingerprint (dataset has no single account ID).
ACCOUNT_FIELDS = ["card1", "card2", "card3", "card4", "card5", "card6", "addr1", "addr2"]

# Identifier fields used to draw edges between accounts, with a base weight
# reflecting how strong a signal that shared value is.
IDENTIFIER_FIELDS = {
    "DeviceInfo": 1.0,
    "id_31": 0.7,   # browser/OS string, from identity table
    "P_emaildomain": 0.4,
    "R_emaildomain": 0.4,
    "addr1": 0.3,
}

# Domains too common to be signal on their own (down-weighted, not excluded outright
# so a *combination* of a common domain + another shared identifier can still count).
COMMON_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "aol.com", "anonymous.com",
    "outlook.com", "icloud.com", "comcast.net", "msn.com", "live.com",
}
COMMON_DOMAIN_WEIGHT_MULTIPLIER = 0.15

# Any identifier value shared by more than this many accounts is treated as noise
# and excluded from edge creation entirely (e.g. a DeviceInfo string that's actually
# a generic "Windows" bucket rather than a real fingerprint).
MAX_ACCOUNTS_PER_IDENTIFIER_VALUE = 40

# Live scoring (section 9): probability at/above this is reported as "flagged".
SCORE_FLAG_THRESHOLD = 0.5
