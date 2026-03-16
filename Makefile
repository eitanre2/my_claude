.PHONY: sync sync-devenv sync-devenv_worker2 sync-gdrive

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
