#!/usr/bin/env python3
"""
Analyze remaining GitHub Issues to identify automation-related ones for cleanup.
"""
import os
from github import Github


def analyze_issues():
    """Analyze all remaining issues to find automation-related ones."""
    github_token = os.getenv('GITHUB_TOKEN')
    repo_name = os.getenv('GITHUB_REPOSITORY')
    
    if not github_token or not repo_name:
        print("❌ GITHUB_TOKEN or GITHUB_REPOSITORY not set")
        return
    
    github = Github(github_token)
    repo = github.get_repo(repo_name)
    
    print(f"🔍 Analyzing all issues in {repo_name}")
    
    # Get all open issues
    open_issues = repo.get_issues(state='open')
    total_open = open_issues.totalCount
    print(f"📊 Total open issues: {total_open}")
    
    # Analyze issues
    automation_keywords = ['automated', 'flickr', 'instagram', 'dry-run', 'posted', 'failed', 'automation', 'album', 'photo']
    
    categories = {
        'automation_related': [],
        'project_issues': []
    }
    
    for issue in open_issues:
        labels = [label.name.lower() for label in issue.labels]
        title_lower = issue.title.lower()
        
        # Check if this is an automation issue
        is_automation = (
            any(keyword in ' '.join(labels) for keyword in automation_keywords) or
            any(keyword in title_lower for keyword in automation_keywords) or
            'photo' in title_lower or
            'posted:' in issue.title or
            'dry run:' in issue.title
        )
        
        if is_automation:
            categories['automation_related'].append({
                'number': issue.number,
                'title': issue.title,
                'labels': [label.name for label in issue.labels],
                'state': issue.state
            })
        else:
            categories['project_issues'].append({
                'number': issue.number,
                'title': issue.title,
                'labels': [label.name for label in issue.labels]
            })
    
    # Report results
    automation_count = len(categories['automation_related'])
    project_count = len(categories['project_issues'])
    
    print(f"\n=== ANALYSIS RESULTS ===")
    print(f"🤖 Automation-related issues: {automation_count}")
    print(f"📋 Actual project issues: {project_count}")
    print(f"📈 Cleanup potential: {automation_count} issues could be closed")
    
    if automation_count > 0:
        print(f"\n=== AUTOMATION ISSUES TO CLOSE ===")
        for issue in categories['automation_related'][:20]:  # Show first 20
            print(f"#{issue['number']}: {issue['title']}")
            if issue['labels']:
                print(f"   Labels: {', '.join(issue['labels'])}")
            print()
    
    if project_count > 0:
        print(f"\n=== ACTUAL PROJECT ISSUES (KEEP) ===")
        for issue in categories['project_issues'][:10]:  # Show first 10
            print(f"#{issue['number']}: {issue['title']}")
            if issue['labels']:
                print(f"   Labels: {', '.join(issue['labels'])}")
            print()
    
    # Provide cleanup recommendation
    if automation_count > 10:
        print(f"\n💡 RECOMMENDATION:")
        print(f"   Run the comprehensive cleanup to close {automation_count} automation issues")
        print(f"   This will leave {project_count} actual project issues")
        print(f"   Command: python cleanup_legacy_issues.py --execute")
    else:
        print(f"\n✅ Repository is already well-organized!")
        print(f"   Only {automation_count} automation issues remaining")


if __name__ == "__main__":
    analyze_issues()