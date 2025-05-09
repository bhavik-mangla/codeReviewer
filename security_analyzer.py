import os
import requests
import json
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from openai import OpenAI

class SecurityAnalyzer:
    def __init__(self, azure_org_url, personal_access_token, openai_api_key):
        # Azure DevOps connection
        self.credentials = BasicAuthentication('', personal_access_token)
        self.connection = Connection(base_url=azure_org_url, creds=self.credentials)
        self.git_client = self.connection.clients.get_git_client()
        
        # OpenAI connection
        self.openai_client = OpenAI(api_key=openai_api_key)
        
        # Knowledge base initialization
        self.load_knowledge_base()
        
    def load_knowledge_base(self):
        # Load security rules, coding standards, etc.
        self.security_rules = json.load(open('security_rules.json'))
        self.coding_standards = json.load(open('coding_standards.json'))
        self.known_vulnerabilities = json.load(open('vulnerabilities.json'))
    
    def get_pr_changes(self, repository_id, pull_request_id):
        # Get the PR differences using Azure DevOps API
        changes = self.git_client.get_pull_request_changes(
            repository_id=repository_id,
            pull_request_id=pull_request_id
        )
        
        return changes
    
    def analyze_code(self, code_content, file_path, language):
        # Perform static analysis
        static_issues = self.perform_static_analysis(code_content, language)
        
        # AI-based analysis
        ai_issues = self.perform_ai_analysis(code_content, file_path, language)
        
        return {
            'static_analysis': static_issues,
            'ai_analysis': ai_issues
        }
    
    def perform_static_analysis(self, code_content, language):
        # Implement rules-based static analysis
        issues = []
        
        for rule in self.security_rules.get(language, []):
            # Check if rule pattern exists in code
            if rule['pattern'] in code_content:
                issues.append({
                    'type': 'security',
                    'severity': rule['severity'],
                    'description': rule['description'],
                    'suggestion': rule['suggestion']
                })
        
        return issues
    
    def perform_ai_analysis(self, code_content, file_path, language):
        # Use OpenAI to analyze code
        prompt = f"""
        Analyze the following {language} code for:
        1. Security vulnerabilities
        2. Optimization opportunities
        3. Adherence to industry coding standards
        
        Code to analyze:
        ```{language}
        {code_content}
        ```
        
        Return results in JSON format with:
        - issue_type: "security", "optimization", or "standard"
        - severity: "critical", "high", "medium", or "low"
        - description: Clear explanation of the issue
        - suggestion: Concrete recommendation to fix the issue
        - line_number: Approximate line number where issue occurs (if possible)
        """
        
        response = self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert security code reviewer."},
                {"role": "user", "content": prompt}
            ]
        )
        
        # Parse the response and return structured issues
        try:
            return json.loads(response.choices[0].message.content)
        except:
            return [{"error": "Failed to parse AI analysis results"}]
    
    def generate_report(self, analysis_results, repository_name, pr_number):
        # Aggregate and format all findings into a comprehensive report
        report = {
            "repository": repository_name,
            "pull_request": pr_number,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "security_issues": sum(1 for result in analysis_results if result.get("issue_type") == "security"),
                "optimization_opportunities": sum(1 for result in analysis_results if result.get("issue_type") == "optimization"),
                "coding_standard_violations": sum(1 for result in analysis_results if result.get("issue_type") == "standard")
            },
            "issues": sorted(analysis_results, key=lambda x: self.get_severity_level(x.get("severity", "low")), reverse=True)
        }
        
        return report
    
    def get_severity_level(self, severity):
        levels = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        return levels.get(severity.lower(), 0)

# Example usage
if __name__ == "__main__":
    # Initialize with your Azure DevOps organization URL and personal access token
    analyzer = SecurityAnalyzer(
        azure_org_url="https://dev.azure.com/your-organization",
        personal_access_token="your-personal-access-token",
        openai_api_key="your-openai-api-key"
    )
    
    # Analyze a specific PR
    repository_id = "your-repository-id"
    pull_request_id = 123
    
    changes = analyzer.get_pr_changes(repository_id, pull_request_id)
    
    all_issues = []
    
    for change in changes.changes:
        if change.change_type == "Edit":
            # Get file content
            file_path = change.item.path
            file_content = get_file_content(repository_id, file_path, change.item.commit_id)
            
            # Determine language based on file extension
            language = determine_language(file_path)
            
            # Analyze the file
            issues = analyzer.analyze_code(file_content, file_path, language)
            all_issues.extend(issues)
    
    # Generate report
    report = analyzer.generate_report(all_issues, "your-repository-name", pull_request_id)
    
    # Output or store the report
    print(json.dumps(report, indent=2))