"""
Utility functions for the AI Security Analyzer
"""
import os
import re
import json
import logging
from pathlib import Path
import fnmatch

logger = logging.getLogger(__name__)

def determine_language(file_path):
    """Determine the programming language based on file extension"""
    ext = os.path.splitext(file_path)[1].lower().lstrip('.')
    
    # Load language mappings from config
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    language_map = config.get('analysis', {}).get('languages', {})
    
    return language_map.get(ext, 'unknown')

def should_skip_file(file_path):
    """Check if a file should be skipped based on patterns in config"""
    with open('config.json', 'r') as f:
        config = json.load(f)
        
    skip_patterns = config.get('analysis', {}).get('skip_files', [])
    
    for pattern in skip_patterns:
        if fnmatch.fnmatch(file_path, pattern):
            return True
    
    return False

def extract_code_snippet(content, line_number, context_lines=3):
    """Extract a code snippet around a specific line"""
    lines = content.splitlines()
    
    if not lines or line_number > len(lines):
        return ""
    
    start = max(0, line_number - context_lines - 1)
    end = min(len(lines), line_number + context_lines)
    
    snippet = []
    for i in range(start, end):
        line_prefix = "→ " if i + 1 == line_number else "  "
        snippet.append(f"{i + 1:4d} {line_prefix}{lines[i]}")
    
    return "\n".join(snippet)

def get_line_number_for_pattern(content, pattern):
    """Find the line number where a pattern appears in the content"""
    lines = content.splitlines()
    
    pattern_re = re.compile(pattern)
    
    for i, line in enumerate(lines):
        if pattern_re.search(line):
            return i + 1
    
    return None

def format_markdown_report(report):
    """Format a report as Markdown for PR comments"""
    md = [f"# AI Security Analysis\n"]
    
    # Add summary section
    md.append("## Summary\n")
    md.append("| Category | Count |\n")
    md.append("| -------- | ----- |\n")
    md.append(f"| 🔴 Critical Security Issues | {report['summary'].get('critical', 0)} |\n")
    md.append(f"| 🟠 High Security Issues | {report['summary'].get('high', 0)} |\n")
    md.append(f"| 🟡 Medium Security Issues | {report['summary'].get('medium', 0)} |\n")
    md.append(f"| 🔵 Low Security Issues | {report['summary'].get('low', 0)} |\n")
    md.append(f"| 🟢 Optimization Opportunities | {report['summary'].get('optimization', 0)} |\n")
    
    # Group issues by file
    files = {}
    for issue in report.get('issues', []):
        file_path = issue.get('file_path', 'Unknown')
        if file_path not in files:
            files[file_path] = []
        files[file_path].append(issue)
    
    # Add each file's issues
    for file_path, issues in files.items():
        md.append(f"\n## File: `{file_path}`\n")
        
        for issue in issues:
            severity = issue.get('severity', 'low')
            severity_icon = {
                'critical': '🔴',
                'high': '🟠',
                'medium': '🟡',
                'low': '🔵'
            }.get(severity.lower(), '⚪')
            
            issue_type = issue.get('issue_type', 'issue')
            line_num = issue.get('line_number', '')
            line_info = f"line {line_num}" if line_num else ""
            
            md.append(f"### {severity_icon} {severity.upper()}: {issue.get('description', 'Unknown issue')}\n")
            
            if line_info:
                md.append(f"**Location:** {line_info}\n")
            
            md.append(f"**Type:** {issue_type}\n")
            
            if 'suggestion' in issue:
                md.append(f"**Suggestion:** {issue['suggestion']}\n")
            
            if 'code_snippet' in issue:
                md.append("**Code:**\n")
                md.append("```\n" + issue['code_snippet'] + "\n```\n")
    
    return "\n".join(md)

def send_notification(report, channel):
    """Send notification about the security analysis report"""
    # Implementation would depend on your notification system (email, Slack, Teams, etc.)
    logger.info(f"Sending notification to {channel}")
    
    # This is a placeholder function - you would implement your notification logic here
    critical_issues = sum(1 for issue in report.get('issues', []) 
                         if issue.get('severity') == 'critical')
    
    high_issues = sum(1 for issue in report.get('issues', []) 
                     if issue.get('severity') == 'high')
    
    if critical_issues > 0:
        logger.info(f"ALERT: {critical_issues} critical security issues found!")
    
    if critical_issues > 0 or high_issues > 0:
        # This would trigger your notification system
        pass