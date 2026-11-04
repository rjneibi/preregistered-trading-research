# Pre-release scans

Before the first push, the repository was scanned for secrets and personal data. Both the working tree and the full git history were scanned. The history is one commit, made fresh for this release.

| Scan | Tool | Target | Result |
|---|---|---|---|
| Secrets | gitleaks 8.30.1, `dir` | Working tree | No leaks, [gitleaks_tree.json](gitleaks_tree.json) |
| Secrets | gitleaks 8.30.1, `git` | Full history | No leaks, [gitleaks_history.json](gitleaks_history.json) |
| Secrets | trufflehog 3.99.7, `filesystem` | Working tree | 0 verified, 0 unverified, 14,775 chunks |
| Secrets | trufflehog 3.99.7, `git` | Full history | 0 verified, 0 unverified, 8,681 chunks |
| Personal data | Pattern scan, see below | Working tree | Every hit reviewed by hand, none is personal data, [deny_scan.txt](deny_scan.txt) |

Trufflehog writes one JSON line per finding, so its reports are empty. Its counts come from its own summary line.

The pattern scan looks for:

- keys and tokens;
- password assignments;
- email addresses, phone numbers and IP addresses;
- absolute paths and usernames;
- broker, server and account names;
- wallet addresses;
- the names of bots and people that must not appear.

It prints counts per file, never the matched text. The hits it reports are:

| Category | What they are |
|---|---|
| `brokers` | Words such as "demo", "live" and "FTMO-style" in prose and code |
| `real_money_word` | Sentences saying that no real money was at risk, and a script that refuses to run against a live account |
| `bot_names` | The study name HLCOPY-1, its folder name and the words "Hyperliquid wallets". No wallet address appears |
| `email` | The `noreply` address in commit trailers written by two scripts |
| `abs_path`, `vm`, `ids` | Byte noise inside the compressed file `all_runs.csv.gz`. Its decompressed text has no hits |

These scans were run on the tree without this folder, so the reports do not scan themselves. They were then run again on the final tree with this folder added. Again no secrets were found, and the only new pattern hits are in this folder's own files.
