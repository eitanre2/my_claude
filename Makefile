.PHONY: sync sync-gdrive diff

GDRIVE_DEST := /Users/eitanrevach/eitan.revach@cloudinary.com - Google Drive/My Drive/AgenticBackup/claude
SYNC_FILES := credentials.json CLAUDE.md settings.json
SYNC_DIRS  := skills rules
DEVENV_HOSTS := devenv2 devenv_worker2

sync: $(addprefix sync-,$(DEVENV_HOSTS)) sync-gdrive

$(addprefix sync-,$(DEVENV_HOSTS)): sync-%:
	ssh $* "mkdir -p ~/.claude"
	$(foreach f,$(SYNC_FILES),scp $(f) $*:~/.claude/;)
	$(foreach d,$(SYNC_DIRS),scp -r $(d) $*:~/.claude/;)

sync-gdrive:
	$(foreach f,$(SYNC_FILES),cp $(f) "$(GDRIVE_DEST)/";)
	$(foreach d,$(SYNC_DIRS),rm -rf "$(GDRIVE_DEST)/$(d)" && cp -r $(d) "$(GDRIVE_DEST)/";)

diff: $(addprefix diff-,$(DEVENV_HOSTS))

$(addprefix diff-,$(DEVENV_HOSTS)): diff-%:
	@echo "══════════════════════════════════════════"
	@echo "  Comparing local vs $*:~/.claude"
	@echo "══════════════════════════════════════════"
	@tmp=$$(mktemp -d); \
	rsync -rlcn --delete --exclude='.DS_Store' --out-format='%i %n' \
		$(SYNC_FILES) $(SYNC_DIRS) $*:~/.claude/ 2>/dev/null > "$$tmp/out" || true; \
	awk '/^<f[^+]/{print $$2}' "$$tmp/out" > "$$tmp/mod"; \
	if [ -s "$$tmp/mod" ]; then \
		while IFS= read -r f; do stat -f %m "$$f" 2>/dev/null || echo 0; done < "$$tmp/mod" > "$$tmp/lt"; \
		ssh $* 'while IFS= read -r f; do stat -c %Y "$$HOME/.claude/$$f" 2>/dev/null || echo 0; done' \
			< "$$tmp/mod" > "$$tmp/rt"; \
		paste "$$tmp/mod" "$$tmp/lt" "$$tmp/rt" > "$$tmp/ts"; \
	else touch "$$tmp/ts"; fi; \
	while read -r flags path _; do \
		case "$$flags" in \
		\*del*)    printf "  %-23s%s\n" "REMOTE ONLY" "$$path" ;; \
		"<f+++"*)  printf "  %-23s%s\n" "LOCAL ONLY" "$$path" ;; \
		"<f"*)     label="MODIFIED"; \
		           tsl=$$(awk -F'\t' -v p="$$path" '$$1==p{print;exit}' "$$tmp/ts"); \
		           lt=$$(printf '%s' "$$tsl" | cut -f2); \
		           rt=$$(printf '%s' "$$tsl" | cut -f3); \
		           if [ -n "$$lt" ] && [ -n "$$rt" ]; then \
		             if [ "$$lt" -gt "$$rt" ] 2>/dev/null; then label="MODIFIED (local >)"; \
		             elif [ "$$lt" -lt "$$rt" ] 2>/dev/null; then label="MODIFIED (remote >)"; fi; \
		           fi; \
		           printf "  %-23s%s\n" "$$label" "$$path" ;; \
		cd*)       ;; \
		*)         printf "  %-23s%s\n" "CHANGED" "$$path" ;; \
		esac; \
	done < "$$tmp/out"; \
	rm -rf "$$tmp"
	@echo ""
	@echo "  (empty = fully in sync)"
	@echo ""
