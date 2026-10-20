# TrendAlgo setup guide

<!-- Generated from src/trendalgo/device/wizard/content.py. Edit that file, then run `python -m trendalgo.device.wizard.guide --write`. -->

## W0: Before you start

TrendAlgo has two parts. The device app runs on this PC for scans, backtests, plans, the journal, and this wizard. A host runs the approved plan on a server you control, 24 hours a day. The device never holds your exchange keys.

Trading can lose money. Start in shadow mode. Shadow mode records what the bot would do and places no real orders.

Never type a password, seed phrase, card number, or withdrawal address into TrendAlgo. This guide and the wizard never ask for them.

## W1: Create a Kraken API key (query-only first)

Sign in to Kraken. Open Settings, select the API tab, and click Create API key.

Start with query-only: Query Funds, Query Open Orders & Trades, Query Closed Orders & Trades. Add Modify Orders and Cancel/Close Orders only when you are ready to trade after shadow mode.

Leave Withdraw Funds unticked. Leave Deposit Funds and Export Data unticked too.

Set the IP restriction to this PC (or your host). Keep optional settings at defaults.

Store the key in the encrypted vault in Settings on this PC (or on the host). Never paste keys into a chat. Saving keys does not enable live trading.

Sources:

- [Kraken: How to create a spot API key](https://support.kraken.com/hc/en-us/articles/360000919966-How-to-generate-an-API-key-pair), checked 2026-10-10

## W2: Practice first, on this PC

Practice mode runs on this PC, on the local address 127.0.0.1. It places no orders and uses no exchange keys.

Finish practice mode before you set up a host. The wizard saves each check you pass, so you can stop and come back later.

## W3: Set up the host on Oracle Cloud

Path A is an Oracle Cloud Always Free Ampere A1 instance. Always Free includes 2 OCPUs and 12 GB of memory for A1 instances. Size the host to that limit, so its usage stays inside the Always Free limits.

Choose your home region before you activate the account. Always Free compute must be created in your home region, and a free-tier account is limited to one subscribed region. Pick the region you will keep.

If Oracle reports "out of host capacity", Always Free shapes are short in your home region for now. Try another availability domain, wait, or upgrade to a paid account. Oracle does not charge for Always Free resources after an upgrade. It charges only for usage above the Always Free limits.

If capacity stays short, choose Path B: a paid VPS on an amd64 or arm64 machine.

Oracle may reclaim idle Always Free compute instances. An instance counts as idle when, over a 7-day period, its 95th-percentile CPU use, its network use, and its memory use are each under 20%. The memory rule applies to A1 shapes.

Create a budget on the root compartment with a low actual-spend alert. Oracle budgets are soft limits. Budget alerts are evaluated every 24 hours, so they are not real-time protection, and they do not stop spending.

Use a static public IP address for the host, so the Kraken key's IP restriction keeps working. If the host's address changes, Kraken blocks the key and orders stop until you update the allowlist.

Sources:

- [Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/), checked 2026-10-10
- [Oracle: Always Free resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm), checked 2026-10-10
- [Oracle: Regions and availability domains](https://docs.oracle.com/en-us/iaas/Content/General/Concepts/regions.htm), checked 2026-10-10
- [Oracle: Budgets](https://docs.oracle.com/en-us/iaas/Content/Billing/Concepts/budgetsoverview.htm), checked 2026-10-10
- [Kraken: How to create a spot API key](https://support.kraken.com/hc/en-us/articles/360000919966-How-to-generate-an-API-key-pair), checked 2026-10-10

## W4: Pair this PC with the host

The host shows a pairing code once, on its console. Enter the code here within 10 minutes. Each code works one time.

Compare the fingerprint the host shows with the fingerprint shown here, one character at a time. Confirm only if they match. If they differ, do not confirm. Stop, and pair again from the host.

Reinstalling the host means pairing again.

## W5: Shadow mode, then go-live

The host starts in shadow mode. Run shadow mode for at least 14 days, and review each difference it finds before you go live.

Live trading needs the go-live checklist. The checklist shows the reclamation risk of Path A and asks you to type an acknowledgment before it allows live orders.

Choose an alert channel you read, and test it before you go live. A stopped host cannot warn you about itself, so check on it often.

Sources:

- [Oracle: Always Free resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm), checked 2026-10-10
