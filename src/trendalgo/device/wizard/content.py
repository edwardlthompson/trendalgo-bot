"""The one content file for the setup wizard and the guide (docs/SETUP_GUIDE.md is generated from it).

Every provider claim cites an official page and the date it was last checked. Change a claim only
after checking the page again, then update its date.
"""

from __future__ import annotations

from datetime import date

from trendalgo.device.wizard.model import Source, Step

CHECKED = date(2026, 10, 10)

ORACLE_FREE = Source("Oracle Cloud Free Tier", "https://www.oracle.com/cloud/free/", CHECKED)
ORACLE_ALWAYS_FREE = Source(
    "Oracle: Always Free resources",
    "https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm",
    CHECKED,
)
ORACLE_REGIONS = Source(
    "Oracle: Regions and availability domains",
    "https://docs.oracle.com/en-us/iaas/Content/General/Concepts/regions.htm",
    CHECKED,
)
ORACLE_BUDGETS = Source(
    "Oracle: Budgets",
    "https://docs.oracle.com/en-us/iaas/Content/Billing/Concepts/budgetsoverview.htm",
    CHECKED,
)
KRAKEN_API_KEY = Source(
    "Kraken: How to create a spot API key",
    "https://support.kraken.com/hc/en-us/articles/360000919966-How-to-generate-an-API-key-pair",
    CHECKED,
)

STEPS: tuple[Step, ...] = (
    Step(
        "W0",
        "Before you start",
        (
            "TrendAlgo has two parts. The device app runs on this PC for scans, backtests, plans, "
            "the journal, and this wizard. A host runs the approved plan on a server you control, "
            "24 hours a day. The device never holds your exchange keys.",
            "Trading can lose money. Start in shadow mode. Shadow mode records what the bot would "
            "do and places no real orders.",
            "Never type a password, seed phrase, card number, or withdrawal address into "
            "TrendAlgo. This guide and the wizard never ask for them.",
        ),
    ),
    Step(
        "W1",
        "Create a Kraken API key for trading",
        (
            "Sign in to Kraken. Open Settings, select the API tab, and click Create API key.",
            "Tick only these permissions: Query Funds, Query Open Orders & Trades, Query Closed "
            "Orders & Trades, Modify Orders, and Cancel/Close Orders.",
            "Leave Withdraw Funds unticked. Leave Deposit Funds and Export Data unticked too.",
            "Set the IP restriction to the static public IP address of your host (Step W3). Keep "
            "the other optional settings at their defaults.",
            "Store the key in an encrypted vault, not in a chat or a plain text file. The host "
            "keeps the key encrypted. This PC does not hold it.",
        ),
        (KRAKEN_API_KEY,),
    ),
    Step(
        "W2",
        "Practice first, on this PC",
        (
            "Practice mode runs on this PC, on the local address 127.0.0.1. It places no orders "
            "and uses no exchange keys.",
            "Finish practice mode before you set up a host. The wizard saves each check you pass, "
            "so you can stop and come back later.",
        ),
    ),
    Step(
        "W3",
        "Set up the host on Oracle Cloud",
        (
            "Path A is an Oracle Cloud Always Free Ampere A1 instance. Always Free includes 2 OCPUs "
            "and 12 GB of memory for A1 instances. Size the host to that limit, so its usage stays "
            "inside the Always Free limits.",
            "Choose your home region before you activate the account. Always Free compute must be "
            "created in your home region, and a free-tier account is limited to one subscribed "
            "region. Pick the region you will keep.",
            'If Oracle reports "out of host capacity", Always Free shapes are short in your home '
            "region for now. Try another availability domain, wait, or upgrade to a paid account. "
            "Oracle does not charge for Always Free resources after an upgrade. It charges only "
            "for usage above the Always Free limits.",
            "If capacity stays short, choose Path B: a paid VPS on an amd64 or arm64 machine.",
            "Oracle may reclaim idle Always Free compute instances. An instance counts as idle "
            "when, over a 7-day period, its 95th-percentile CPU use, its network use, and its "
            "memory use are each under 20%. The memory rule applies to A1 shapes.",
            "Create a budget on the root compartment with a low actual-spend alert. Oracle "
            "budgets are soft limits. Budget alerts are evaluated every 24 hours, so they are not "
            "real-time protection, and they do not stop spending.",
            "Use a static public IP address for the host, so the Kraken key's IP restriction keeps "
            "working. If the host's address changes, Kraken blocks the key and orders stop until "
            "you update the allowlist.",
        ),
        (ORACLE_FREE, ORACLE_ALWAYS_FREE, ORACLE_REGIONS, ORACLE_BUDGETS, KRAKEN_API_KEY),
    ),
    Step(
        "W4",
        "Pair this PC with the host",
        (
            "The host shows a pairing code once, on its console. Enter the code here within "
            "10 minutes. Each code works one time.",
            "Compare the fingerprint the host shows with the fingerprint shown here, one character "
            "at a time. Confirm only if they match. If they differ, do not confirm. Stop, and pair "
            "again from the host.",
            "Reinstalling the host means pairing again.",
        ),
    ),
    Step(
        "W5",
        "Shadow mode, then go-live",
        (
            "The host starts in shadow mode. Run shadow mode for at least 14 days, and review each "
            "difference it finds before you go live.",
            "Live trading needs the go-live checklist. The checklist shows the reclamation risk of "
            "Path A and asks you to type an acknowledgment before it allows live orders.",
            "Choose an alert channel you read, and test it before you go live. A stopped host "
            "cannot warn you about itself, so check on it often.",
        ),
        (ORACLE_ALWAYS_FREE,),
    ),
)
