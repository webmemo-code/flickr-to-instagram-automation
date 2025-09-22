#!/bin/bash

# Script to fix commit messages using interactive rebase
# WARNING: This will rewrite git history. Only run this on a backed-up repository.

echo "=== COMMIT MESSAGE FIXING SCRIPT ==="
echo "This script will use interactive rebase to fix commit messages from d828f2b onwards"
echo ""
echo "IMPORTANT: This will rewrite git history!"
echo "Make sure you have a backup of your repository before proceeding."
echo ""
read -p "Do you want to continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "=== RECONSTRUCTED COMMIT MESSAGES ==="
echo "Based on file analysis, here are the proposed commit messages:"
echo ""

cat << 'EOF'
Commit 8554828 (merge):
REFACTOR | Merge workflow improvements and backup archival

Commit 95d60b9:
REFACTOR | Archive backup workflows and clean temporary files

Commit 3ed81e4 (merge):
UPDATE | Merge enhanced blog content and caption generation features

Commit c58f69e:
UPDATE | Add multi-language caption generation with enhanced blog integration

Commit b0f2614 (merge):
UPDATE | Merge blog content extractor improvements

Commit bd8d210:
UPDATE | Enhance blog content extraction functionality

Commit f9cc7b8:
REFACTOR | Improve configuration management and account handling

Commit 643580f:
TESTING | Expand test suite for blog content and caption generation

Commit e402a58:
UPDATE | Add EXIF URL prioritization and multi-language support

Commit 78f9935:
REFACTOR | Restructure account configuration architecture

Commit 36111d9:
UPDATE | Implement WordPress authentication for blog content access

Commit 3d0e43f:
REFACTOR | Enhance state management and migration utilities

Commit 4488727:
UPDATE | Add advanced caption generation with account-specific branding

Commit 9682b83:
DOCS | Update README and architecture documentation

Commit 8f6e97e:
UPDATE | Implement storage adapter pattern for enhanced state management

Commit ffe27a6:
REFACTOR | Improve configuration validation and loading

Commit e626ca7:
UPDATE | Add comprehensive blog content extraction with authentication
EOF

echo ""
echo "=== INTERACTIVE REBASE COMMAND ==="
echo "Run this command to start the interactive rebase:"
echo ""
echo "git rebase -i d828f2b"
echo ""
echo "In the editor that opens:"
echo "1. Change 'pick' to 'reword' for each commit you want to change"
echo "2. Save and exit"
echo "3. For each commit, you'll be prompted to enter the new message"
echo "4. Use the messages listed above, following this format:"
echo ""
echo "[PREFIX] | [Description]"
echo ""
echo "Co-Authored-By: Claude <noreply@anthropic.com>"
echo "Co-Authored-By: webmemo-code <walter@webmemo.ch>"
echo ""
echo "=== SAFETY NOTES ==="
echo "- This will change commit hashes"
echo "- If this is a shared repository, coordinate with other developers"
echo "- Consider creating a backup branch first: git branch backup-before-rebase"
echo ""
read -p "Press Enter to continue with the interactive rebase, or Ctrl+C to abort..."

# Create backup branch
echo "Creating backup branch..."
git branch backup-before-rebase

# Start interactive rebase
echo "Starting interactive rebase from d828f2b..."
git rebase -i d828f2b