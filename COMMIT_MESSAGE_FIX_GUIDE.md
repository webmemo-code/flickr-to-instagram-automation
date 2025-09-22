# Git Commit Message Fix Guide

## Overview
This guide helps you safely replace empty commit messages with proper ones following the project's convention.

## ⚠️ Important Safety Notes

1. **Backup First**: This operation rewrites git history
2. **Local Only**: Only do this if you haven't pushed to a shared repository
3. **Coordinate**: If others have cloned this repo, coordinate the change

## Pre-Flight Checklist

```bash
# 1. Create a backup branch
git branch backup-before-rebase

# 2. Verify current state
git log --oneline -20

# 3. Confirm the last good commit
git show d828f2b
```

## Commit Messages to Apply

Based on file analysis, use these messages during interactive rebase:

### 8554828 (Merge Commit)
```
REFACTOR | Merge workflow improvements and backup archival

Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: webmemo-code <walter@webmemo.ch>
```

### 95d60b9
```
REFACTOR | Archive backup workflows and clean temporary files

Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: webmemo-code <walter@webmemo.ch>
```

### 3ed81e4 (Merge Commit)
```
UPDATE | Merge enhanced blog content and caption generation features

Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: webmemo-code <walter@webmemo.ch>
```

### c58f69e
```
UPDATE | Add multi-language caption generation with enhanced blog integration

Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: webmemo-code <walter@webmemo.ch>
```

### b0f2614 (Merge Commit)
```
UPDATE | Merge blog content extractor improvements

Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: webmemo-code <walter@webmemo.ch>
```

### bd8d210
```
UPDATE | Enhance blog content extraction functionality

Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: webmemo-code <walter@webmemo.ch>
```

### f9cc7b8
```
REFACTOR | Improve configuration management and account handling

Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: webmemo-code <walter@webmemo.ch>
```

### 643580f
```
TESTING | Expand test suite for blog content and caption generation

Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: webmemo-code <walter@webmemo.ch>
```

### e402a58
```
UPDATE | Add EXIF URL prioritization and multi-language support

Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: webmemo-code <walter@webmemo.ch>
```

### 78f9935
```
REFACTOR | Restructure account configuration architecture

Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: webmemo-code <walter@webmemo.ch>
```

### 36111d9
```
UPDATE | Implement WordPress authentication for blog content access

Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: webmemo-code <walter@webmemo.ch>
```

### 3d0e43f
```
REFACTOR | Enhance state management and migration utilities

Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: webmemo-code <walter@webmemo.ch>
```

### 4488727
```
UPDATE | Add advanced caption generation with account-specific branding

Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: webmemo-code <walter@webmemo.ch>
```

### 9682b83
```
DOCS | Update README and architecture documentation

Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: webmemo-code <walter@webmemo.ch>
```

### 8f6e97e
```
UPDATE | Implement storage adapter pattern for enhanced state management

Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: webmemo-code <walter@webmemo.ch>
```

### ffe27a6
```
REFACTOR | Improve configuration validation and loading

Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: webmemo-code <walter@webmemo.ch>
```

### e626ca7
```
UPDATE | Add comprehensive blog content extraction with authentication

Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: webmemo-code <walter@webmemo.ch>
```

## Step-by-Step Process

### 1. Start Interactive Rebase
```bash
git rebase -i d828f2b
```

### 2. Mark Commits for Reword
In the editor that opens, change `pick` to `reword` for each commit:
```
reword 8554828
reword 95d60b9
reword 3ed81e4
reword c58f69e
reword b0f2614
reword bd8d210
reword f9cc7b8
reword 643580f
reword e402a58
reword 78f9935
reword 36111d9
reword 3d0e43f
reword 4488727
reword 9682b83
reword 8f6e97e
reword ffe27a6
reword e626ca7
```

### 3. Apply Messages
For each commit, git will open an editor. Replace the empty message with the corresponding message from above.

### 4. Verify Results
```bash
# Check that all commits now have proper messages
git log --oneline -20

# Verify specific commits
git show --format=fuller 8554828
```

## Recovery (If Something Goes Wrong)

If the rebase fails or you want to undo:
```bash
# Abort current rebase
git rebase --abort

# Or restore from backup
git checkout backup-before-rebase
git branch -D main
git checkout -b main
```

## Cleanup After Success

```bash
# Delete backup branch
git branch -D backup-before-rebase

# If you had already pushed, force push (DANGEROUS - coordinate with team)
# git push --force-with-lease origin main
```

## Convention Reference

Format: `[PREFIX] | [Description]`

**Prefixes:**
- **PLANNING** | For initial plans, PRDs, to dos
- **BUILDING** | Initial artifacts before first stable version
- **DOCS** | Documentation tasks
- **UPDATE** | Adding functionality to stable version
- **FIXING** | Intermediate fixes
- **FIXED** | When fixing is complete
- **REFACTOR** | Architectural changes, variable renamings
- **SECURITY** | Security fixes
- **TESTING** | Testing procedures

**Co-Author Format:**
```
Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: webmemo-code <walter@webmemo.ch>
```