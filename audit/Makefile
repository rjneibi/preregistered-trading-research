.PHONY: audit trace

# Clean clone, fresh pinned environments, sandboxes rebuilt from the originals, all stages rerun, output hashes compared.
audit:
	bash tools/make_audit.sh

trace:
	python stats/traceability.py
