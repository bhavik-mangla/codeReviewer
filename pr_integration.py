"""
Integration with Azure DevOps PR system
"""
import base64
import logging
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from azure.devops.v6_0.git import GitClient, CommentThreadStatus, CommentType

logger = logging.getLogger(__name__)

class PRIntegration:
    def __init__(self, azure_org_url, personal_access_token):
        """Initialize PR integration with Azure DevOps"""
        self.credentials = BasicAuthentication('', personal_access_token)
        self.connection = Connection(base_url=azure_org_url, creds=self.credentials)
        self.git_client = self.connection.clients.get_git_client()
    
    def get_file_content(self, repository_id, file_path, commit_id):
        """Get file content from the repository at a specific commit"""
        try:
            item = self.git_client.get_item(
                repository_id=repository_id,
                path=file_path,
                version=commit_id
            )
            
            if item.content:
                # If content is returned directly
                content = base64.b64decode(item.content).decode('utf-8')
            else:
                # If we need to download the content
                content_stream = self.git_client.get_item_content(
                    repository_id=repository_id,
                    path=file_path,
                    download=True,
                    version=commit_id
                )
                content = content_stream.decode('utf-8')
            
            return content
        except Exception as e:
            logger.error(f"Error retrieving file content for {file_path}: {e}")
            return ""
    
    def get_repository_name(self, repository_id):
        """Get repository name from repository ID"""
        try:
            repo = self.git_client.get_repository(repository_id)
            return repo.name
        except Exception as e:
            logger.error(f"Error retrieving repository name: {e}")
            return repository_id
    
    def post_pr_comment(self, repository_id, pull_request_id, comment_content):
        """Post a comment to the PR"""
        try:
            from azure.devops.v6_0.git.models import Comment, CommentThread
            
            # Create a comment thread
            thread = CommentThread(
                comments=[
                    Comment(
                        content=comment_content,
                        comment_type=CommentType.text
                    )
                ],
                status=CommentThreadStatus.active
            )
            
            # Post the thread to the PR
            self.git_client.create_thread(
                comment_thread=thread,
                repository_id=repository_id,
                pull_request_id=pull_request_id
            )
            
            logger.info(f"Posted comment to PR #{pull_request_id}")
            return True
        except Exception as e:
            logger.error(f"Error posting PR comment: {e}")
            return False
    
    def post_file_comment(self, repository_id, pull_request_id, file_path, line_number, comment_content):
        """Post a comment on a specific file and line in the PR"""
        try:
            from azure.devops.v6_0.git.models import Comment, CommentThread, ItemPath, CommentPosition
            
            # Create a file position for the comment
            position = CommentPosition(
                line=line_number,
                line_type=1  # 1 for original file
            )
            
            # Create the file path reference
            item_path = ItemPath(
                path=file_path
            )
            
            # Create a comment thread
            thread = CommentThread(
                comments=[
                    Comment(
                        content=comment_content,
                        comment_type=CommentType.text
                    )
                ],
                status=CommentThreadStatus.active,
                thread_context={
                    "filePath": file_path,
                    "position": position,
                    "rightFileStart": {
                        "line": line_number
                    }
                }
            )
            
            # Post the thread to the PR
            self.git_client.create_thread(
                comment_thread=thread,
                repository_id=repository_id,
                pull_request_id=pull_request_id
            )
            
            logger.info(f"Posted comment to PR #{pull_request_id} on file {file_path} line {line_number}")
            return True
        except Exception as e:
            logger.error(f"Error posting file comment: {e}")
            return False