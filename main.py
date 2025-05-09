#!/usr/bin/env python3
"""
AI Security Analyzer - Main entry point
"""
import os
import argparse
import json
import logging
from datetime import datetime
from security_analyzer import SecurityAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("security_analyzer.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("security_analyzer")

def parse_args():
    parser = argparse.ArgumentParser(description='AI Security Analyzer')
    parser.add_argument('--org', type=str, required=True, help='Azure DevOps organization URL')
    parser.add_argument('--repo-id', type=str, required=True, help='Repository ID')
    parser.add_argument('--pr-id', type=int, required=True, help='Pull Request ID')
    parser.add_argument('--output', type=str, default='report.json', help='Output report filename')
    parser.add_argument('--config', type=str, default='config.json', help='Configuration file path')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    
    return parser.parse_args()

def load_config(config_path):
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise

def main():
    args = parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info(f"Starting security analysis for PR #{args.pr_id} in repository {args.repo_id}")
    
    try:
        # Load configuration
        config = load_config(args.config)
        
        # Get credentials from environment or config
        pat = os.environ.get('AZURE_DEVOPS_PAT') or config.get('azure_devops_pat')
        openai_key = os.environ.get('OPENAI_API_KEY') or config.get('openai_api_key')
        
        if not pat or not openai_key:
            logger.error("Missing required credentials. Set AZURE_DEVOPS_PAT and OPENAI_API_KEY environment variables or provide them in config.json")
            return 1
        
        # Initialize analyzer
        analyzer = SecurityAnalyzer(
            azure_org_url=args.org,
            personal_access_token=pat,
            openai_api_key=openai_key
        )
        
        # Get PR changes
        logger.info("Fetching PR changes...")
        changes = analyzer.get_pr_changes(args.repo_id, args.pr_id)
        
        # Process each changed file
        all_issues = []
        processed_files = 0
        
        for change in changes.changes:
            if hasattr(change, 'item') and hasattr(change, 'change_type'):
                if change.change_type in ["Add", "Edit"]:
                    try:
                        # Get file content
                        file_path = change.item.path
                        logger.debug(f"Processing file: {file_path}")
                        
                        file_content = analyzer.get_file_content(args.repo_id, file_path, change.item.commit_id)
                        
                        # Determine language based on file extension
                        language = analyzer.determine_language(file_path)
                        
                        # Analyze the file
                        issues = analyzer.analyze_code(file_content, file_path, language)
                        all_issues.extend(issues.get('static_analysis', []))
                        all_issues.extend(issues.get('ai_analysis', []))
                        
                        processed_files += 1
                    except Exception as e:
                        logger.error(f"Error processing file {file_path}: {e}")
        
        logger.info(f"Analyzed {processed_files} files, found {len(all_issues)} issues")
        
        # Get repository name for the report
        repo_name = analyzer.get_repository_name(args.repo_id)
        
        # Generate report
        report = analyzer.generate_report(all_issues, repo_name, args.pr_id)
        
        # Save report to file
        with open(args.output, 'w') as f:
            json.dump(report, indent=2, fp=f)
        
        logger.info(f"Report saved to {args.output}")
        
        # Post comments to PR (if enabled in config)
        if config.get('post_comments', False):
            logger.info("Posting comments to PR...")
            analyzer.post_pr_comments(args.repo_id, args.pr_id, all_issues)
        
        return 0
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit(main())