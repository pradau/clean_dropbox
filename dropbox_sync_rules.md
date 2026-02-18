# Dropbox Sync & Deletion Rules

A reference for understanding how Dropbox handles files, ignore rules, and deletions — particularly relevant when writing tools that interact with your Dropbox folder.

---

## How Sync Works

Dropbox maintains three distinct locations for any file:

- **Local** — the file on your machine inside `~/Dropbox`
- **Cloud** — the canonical copy on Dropbox servers
- **Other devices** — synced copies on your other machines

The cloud is the source of truth. Changes flow: local → cloud → other devices.

---

## Ignore Rules (`rules.dropboxignore`)

- Stored at `~/Dropbox/rules.dropboxignore`
- **Local to each machine** — rules do not sync across devices
- Rules take effect immediately on save
- Supports wildcards (`*.dmg`), paths (`project/**/*.obj`), and folder names (`node_modules/`)
- Lines starting with `#` are comments and ignored

### What ignore rules do and don't do

| Scenario                                            | Result                                                    |
| --------------------------------------------------- | --------------------------------------------------------- |
| File matches rule, never synced                     | Stays local, never uploaded                               |
| File matches rule, already synced to cloud          | Removed from local, remains in cloud                      |
| File already local + in cloud, rule added later     | Removed from local, remains in cloud                      |
| File moved into local Dropbox folder after rule set | Stays local, not uploaded                                 |
| Rule removed                                        | File re-syncs from cloud to local (if it exists in cloud) |

**Key implication for your script:** files matching ignore rules that are currently local may or may not exist in the cloud. The script cannot know without querying the Dropbox API.

---

## Deletion Behavior

### Deleting locally

- Dropbox syncs the deletion to the cloud and all other devices
- File goes to **Dropbox's trash** (recoverable for 30 days on Free/Plus, 180 days on Business)
- This is what happens when you delete from within `~/Dropbox` via Finder or your script

### Deleting from dropbox.com

- Removed from cloud and synced to all devices (removed locally too)
- Also goes to Dropbox trash

### Deleting from the Dropbox app (selective sync)

- Removes from local only, keeps in cloud — this is *not* deletion, it's deselection

---

## Selective Sync vs Ignore Rules

These are often confused but behave differently:

|                              | Selective Sync          | Ignore Rules                  |
| ---------------------------- | ----------------------- | ----------------------------- |
| Configured in                | Dropbox app preferences | `rules.dropboxignore`         |
| Syncs setting across devices | Yes                     | No                            |
| Affects cloud copy           | No (keeps in cloud)     | No (keeps in cloud)           |
| Pattern matching             | Folder-level only       | Files and folders, wildcards  |
| Primary use                  | Save local disk space   | Keep certain files local-only |

---

## What Stays in the Cloud After You Run the Script

Running the cleanup script (with `--move` or `--delete`) removes files **from local only** if they were already synced. Files that were never synced (because the ignore rule was in place when they arrived) were never in the cloud to begin with.

| File history                          | After local deletion         |
| ------------------------------------- | ---------------------------- |
| Was synced before rule was added      | Still in Dropbox cloud trash |
| Never synced (rule predated the file) | Gone entirely — not in cloud |

This distinction matters if you're trying to recover a file later.

---

## Practical Workflow for the Cleanup Script

1. **Dry run** — identify what matches your ignore rules locally
2. **Move to staging** (`~/Data/dropbox_ignored_cleanup/`) — get files out of Dropbox folder so Dropbox stops managing them, without permanent deletion
3. **Let Dropbox settle** — after the move, Dropbox will sync those deletions to the cloud (files go to Dropbox trash)
4. **Review staging folder** — rescue anything you want to keep
5. **Delete staging folder** — permanent local removal of everything you don't need

The staging step is valuable because once a file is moved out of `~/Dropbox`, it's no longer Dropbox's concern — you have full control without Dropbox potentially re-downloading it from the cloud.

---

## Edge Cases to Be Aware Of

- **Directory matches** — if a folder like `node_modules/` matches a rule, all its contents match too. Your script should avoid double-counting or double-deleting children when the parent folder is already matched.
- **Symlinks** — Dropbox does not sync symlinks; they'll appear local-only regardless of rules.
- **In-progress sync** — deleting or moving a file while Dropbox is actively syncing it can cause conflicts. Best to pause Dropbox sync before running the script.
- **`.dropbox` and `.dropbox.cache`** — system files Dropbox manages internally; avoid touching these.
