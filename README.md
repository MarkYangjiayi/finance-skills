# finance-skills — retired

The maintained research repository is now **stock_research** (equity-data v0.5.0).
It contains the four supported skills, shared provider adapters, versioned
financial/valuation calculations, macro analysis, watchlist reports and observed
sentiment workflows.

Use the sibling checkout's README and docs/repository-migration.md for setup.
The old simplified valuation scripts and duplicate equity-research skill are no
longer installed. Financial-statement-analysis is a route within equity-research.

All original files and history are retained at commit
8bc3ccb8d590ee0c9f8a0db92e322b033ce3acc8. The maintained repository also includes
that history at tag `archive/finance-skills-before-migration`.

`./install.sh` delegates to the new checkout's backup-safe skill manager.
Set EQUITY_DATA_REPO if the maintained checkout is not ../stock_research.
Existing conflicting skill copies require --adopt-existing and are backed up.
No network publication or remote repository archiving is performed by this change.
