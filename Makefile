.PHONY: verify data audit audit-public reproduce trace

# No data needed. Hashes, tests, number tracing, links, paths.
verify:
	python scripts/verify.py

# Public datasets into data/raw.
data:
	python scripts/download_data.py

# Clean clone, fresh pinned environments, all stages, output hashes compared. Needs the broker exports too.
audit:
	bash audit/tools/make_audit.sh ../_audit_clean full

# The same, skipping stages that need broker exports.
audit-public:
	bash audit/tools/make_audit.sh ../_audit_clean public

reproduce: audit-public

trace:
	cd audit && python stats/traceability.py
