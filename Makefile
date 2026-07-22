.PHONY: serve build figures new-pattern check-symptoms check-interactions check-template clean

serve:
	mdbook serve --open

build:
	mdbook build

figures:
	@for sim in checkpoint_interval_tradeoff interconnect_scaling_curve \
	            data_loading_gpu_utilization gang_scheduling_fragmentation \
	            preemption_wasted_work etcd_watch_fanout_latency \
	            batching_latency_throughput cold_start_vs_warm_pool_cost \
	            backfill_cost_explosion; do \
	  echo "==> $$sim"; \
	  uv run python sims/$$sim/sim.py --out src/figures/$$sim; \
	done

new-pattern:
ifndef NAME
	$(error NAME is required. Usage: make new-pattern NAME=my-pattern [SECTION=gpu-scheduling])
endif
	$(eval _SECTION := $(if $(SECTION),$(SECTION),))
	$(eval _DIR := $(if $(SECTION),src/patterns/$(SECTION),src/patterns))
	$(eval _DEST := $(_DIR)/$(NAME).md)
	@test ! -f $(_DEST) || (echo "Already exists: $(_DEST)"; exit 1)
	@mkdir -p $(_DIR)
	@cp templates/pattern.md $(_DEST)
	@echo "Created $(_DEST)"
	@echo "Remember to add it to src/SUMMARY.md"

check-symptoms:
	uv run python scripts/check_symptoms.py

check-interactions:
	uv run python scripts/check_interactions.py

check-template:
	uv run python scripts/check_template.py

clean:
	rm -rf book/
