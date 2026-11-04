# Contributing

This repository is a record of tests that mostly failed, kept so others can check them and build on them. Contributions are welcome if they keep the same discipline: decide the test before seeing the result, count every variant, and publish the result whatever it is.

## Ways to contribute

| You want to | Do this |
|---|---|
| Report a wrong number, broken link or mislabelled result | Open an issue with the **Report an error** template. Name the file, the line and the evidence file that disagrees |
| Propose a new test | Open an issue with the **Propose a test** template, then follow [ADD_AN_EXPERIMENT.md](ADD_AN_EXPERIMENT.md) |
| Pick up an open question | See [RESEARCH_AGENDA.md](RESEARCH_AGENDA.md), which lists ideas with the files to start from |
| Rerun the audit | See [REPRODUCE.md](REPRODUCE.md) |

## Rules for a new test

1. **Preregister first.** Write the spec from [experiments/_template/spec.md](experiments/_template/spec.md) and commit it before running anything on the test data. The commit time is the freeze time. Later changes go in a dated deviations section, never into the frozen text.
2. **Count every variant.** Every configuration run, including ones dropped early, goes into the ledger. A contribution's variants are counted in its own rows, with `programme_or_family` set to `contrib:<your-handle>`. The deflated Sharpe is reported twice: at your own count, and at the full ledger count, which is the stricter one.
3. **Touch the holdout once.** Do not tune after looking at out-of-sample or holdout results. If you do look, say so, and the test is graded as exploratory.
4. **Use the common gates.** [audit/prereg/COMMON.md](audit/prereg/COMMON.md) defines the gates the audit used. Say which ones apply and fix their thresholds in the spec.
5. **Report costs you can defend.** State the spread, commission and slippage, and where they came from. Gross-only results are labelled as such.
6. **Label small samples.** Any figure from fewer than 100 trades is `INSUFFICIENT SAMPLE`. Never quote a profit factor without its trade count.
7. **Keep it deterministic.** Fix seeds and set `PYTHONHASHSEED=0`. Pin package versions.

## What not to submit

- Licensed or vendor market data. Add a row to [data/manifest.csv](data/manifest.csv) and a download step instead.
- Credentials, account numbers, broker server names or personal paths.
- Strategies or signals you do not have the right to publish.
- Claims of live profitability. This repository records research, not trading advice.

## Before a pull request

- `python scripts/verify.py` passes.
- New docs link only to files that exist in the repository.
- The ledger and the registry rows are added, and the experiment page follows [experiments/_template/README.md](experiments/_template/README.md).

Code is MIT-licensed and documents are CC BY 4.0, see [LICENSE](LICENSE) and [LICENSE-docs](LICENSE-docs). By contributing you agree to release your contribution under the same terms.
