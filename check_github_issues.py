#!/usr/bin/env python3
"""
Simple diagnostic script to check GitHub Issues using gh CLI.
"""
import subprocess
import json
import sys

def run_gh_command(cmd):
    """Run a GitHub CLI command and return the result."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"Error running command: {cmd}")
            print(f"Error: {result.stderr}")
            return None
    except Exception as e:
        print(f"Exception running command: {e}")
        return None

def main():
    """Check current album status using GitHub CLI."""
    print("=== 🔍 GitHub Issues Diagnostic ===\n")
    
    # Check if gh CLI is available
    gh_version = run_gh_command("gh --version")
    if not gh_version:
        print("❌ GitHub CLI (gh) not found. Please install it first.")
        print("Install from: https://cli.github.com/")
        return
    
    print(f"✅ GitHub CLI found: {gh_version.split()[2]}")
    
    # Set repo (update this to your actual repo)
    repo = "webmemo-code/flickr-to-instagram-automation"
    print(f"📂 Checking repository: {repo}\n")
    
    # Get issues with different labels
    labels_to_check = [
        ("posted", "automated-post,instagram,flickr-album,posted"),
        ("failed", "automated-post,instagram,flickr-album,failed"), 
        ("dry-run", "automated-post,dry-run,flickr-album"),
        ("all-automation", "automated-post,flickr-album")
    ]
    
    results = {}
    
    for label_name, label_query in labels_to_check:
        print(f"🔍 Checking {label_name} issues...")
        cmd = f'gh issue list --repo {repo} --label "{label_query}" --state all --json number,title,labels,createdAt --limit 100'
        output = run_gh_command(cmd)
        
        if output:
            try:
                issues = json.loads(output)
                results[label_name] = issues
                print(f"   Found {len(issues)} {label_name} issues")
            except json.JSONDecodeError:
                print(f"   Error parsing JSON for {label_name}")
                results[label_name] = []
        else:
            results[label_name] = []
    
    # Summary
    print(f"\n📊 Summary:")
    print(f"Successfully posted photos: {len(results['posted'])}")
    print(f"Failed photos: {len(results['failed'])}")
    print(f"Dry run selections: {len(results['dry-run'])}")
    print(f"Total automation issues: {len(results['all-automation'])}")
    
    processed_count = len(results['posted']) + len(results['failed'])
    print(f"Total processed (posted + failed): {processed_count}")
    
    # Show recent issues
    if results['all-automation']:
        print(f"\n📋 Recent automation issues:")
        for issue in results['all-automation'][:5]:
            labels = [label['name'] for label in issue['labels']]
            status = "✅ POSTED" if 'posted' in labels else "❌ FAILED" if 'failed' in labels else "🧪 DRY-RUN" if 'dry-run' in labels else "❓ UNKNOWN"
            print(f"   #{issue['number']}: {issue['title'][:60]}... - {status}")
    
    # Check for recent automation runs
    print(f"\n🤖 Checking automation run logs...")
    cmd = f'gh issue list --repo {repo} --label "automation-log,flickr-album" --state all --json number,title,createdAt --limit 5'
    output = run_gh_command(cmd)
    
    if output:
        try:
            runs = json.loads(output)
            print(f"   Found {len(runs)} recent automation runs:")
            for run in runs:
                print(f"   #{run['number']}: {run['title']}")
        except:
            print("   Error parsing automation runs")

if __name__ == "__main__":
    main()