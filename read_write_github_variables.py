"""
GitHub Repository Variables API - Complete Implementation Guide
===============================================================

This module provides comprehensive functionality for reading and writing GitHub repository
variables programmatically. It addresses the critical issues in the flickr-to-instagram-automation
system where GITHUB_TOKEN cannot write variables and environment isolation affects variable access.

Key Findings from Research:
--------------------------
1. GITHUB_TOKEN CANNOT write repository variables (only read)
2. Personal Access Token (PAT) with 'repo' scope required for write operations
3. Environment variables ('production-social-media') may override repository variables
4. GitHub Actions workflows need proper environment context for variable access

Author: Claude AI Assistant
Created: August 16, 2025
"""

import os
import json
import logging
import requests
from typing import Optional, Dict, List, Any
from github import Github
from github.GithubException import GithubException


class GitHubVariablesManager:
    """
    Complete GitHub repository variables management with environment support.
    
    Handles both repository-level and environment-specific variables with proper
    authentication and error handling for GitHub Actions automation.
    """
    
    def __init__(self, repo_name: str, read_token: str = None, write_token: str = None):
        """
        Initialize GitHub Variables Manager.
        
        Args:
            repo_name: Repository name in "owner/repo" format
            read_token: Token for read operations (GITHUB_TOKEN works)
            write_token: Token for write operations (requires PAT with 'repo' scope)
        """
        self.repo_name = repo_name
        
        # Use environment variables as fallback
        self.read_token = read_token or os.getenv('GITHUB_TOKEN')
        self.write_token = write_token or os.getenv('PERSONAL_ACCESS_TOKEN') or self.read_token
        
        # GitHub API clients
        self.read_github = Github(self.read_token) if self.read_token else None
        self.write_github = Github(self.write_token) if self.write_token else None
        
        # Repository objects
        self.read_repo = None
        self.write_repo = None
        
        if self.read_github:
            try:
                self.read_repo = self.read_github.get_repo(repo_name)
            except Exception as e:
                self.logger.error(f"Failed to get read repository: {e}")
        
        if self.write_github:
            try:
                self.write_repo = self.write_github.get_repo(repo_name)
            except Exception as e:
                self.logger.error(f"Failed to get write repository: {e}")
        
        # Current environment context
        self.current_environment = os.getenv('GITHUB_ENV_NAME', 'default')
        
        # API headers for direct REST calls
        self.headers = {
            'Accept': 'application/vnd.github+json',
            'Authorization': f'Bearer {self.write_token}',
            'X-GitHub-Api-Version': '2022-11-28'
        }
        
        self.logger = logging.getLogger(__name__)
        
        # Validate setup
        self._validate_setup()
    
    def _validate_setup(self):
        """Validate token permissions and access."""
        try:
            if self.read_repo:
                repo_info = self.read_repo.full_name
                self.logger.debug(f"✅ Read access confirmed for {repo_info}")
            elif self.read_github:
                self.logger.warning(f"⚠️ Read GitHub client available but repository access failed")
            
            if self.write_github and self.write_token != self.read_token:
                self.logger.debug(f"✅ Write token configured (PAT)")
            elif self.write_token == self.read_token:
                self.logger.warning(f"⚠️ Using same token for read/write - may lack write permissions")
            
            self.logger.debug(f"Environment context: {self.current_environment}")
            
        except Exception as e:
            self.logger.error(f"❌ Setup validation failed: {e}")
    
    # ===== REPOSITORY VARIABLES (Standard Scope) =====
    
    def get_repository_variable(self, name: str, default: str = "") -> str:
        """
        Get repository variable value.
        
        Args:
            name: Variable name
            default: Default value if variable not found
            
        Returns:
            Variable value or default
        """
        try:
            if not self.read_repo:
                self.logger.error("No repository read access available")
                return default
                
            variable = self.read_repo.get_variable(name)
            value = variable.value
            self.logger.debug(f"Retrieved repository variable {name}: {len(value)} chars")
            return value
            
        except GithubException as e:
            if e.status == 404:
                self.logger.debug(f"Repository variable {name} not found")
            else:
                self.logger.error(f"Failed to get repository variable {name}: {e}")
            return default
        except Exception as e:
            self.logger.error(f"Unexpected error getting repository variable {name}: {e}")
            return default
    
    def set_repository_variable(self, name: str, value: str) -> bool:
        """
        Set repository variable value.
        
        Args:
            name: Variable name
            value: Variable value
            
        Returns:
            True if successful, False otherwise
        """
        if not self.write_token:
            self.logger.error("No write token configured")
            return False
        
        # Use direct REST API for better error handling
        try:
            # Try update first (PATCH)
            url = f"https://api.github.com/repos/{self.repo_name}/actions/variables/{name}"
            data = {"name": name, "value": value}
            
            response = requests.patch(url, headers=self.headers, json=data)
            
            if response.status_code == 204:
                self.logger.debug(f"✅ Updated repository variable {name}")
                return True
            elif response.status_code == 404:
                # Variable doesn't exist, create it (POST)
                url = f"https://api.github.com/repos/{self.repo_name}/actions/variables"
                response = requests.post(url, headers=self.headers, json=data)
                
                if response.status_code == 201:
                    self.logger.debug(f"✅ Created repository variable {name}")
                    return True
                else:
                    self.logger.error(f"❌ Failed to create repository variable {name}: {response.status_code} - {response.text}")
                    return False
            else:
                self.logger.error(f"❌ Failed to update repository variable {name}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Exception setting repository variable {name}: {e}")
            return False
    
    def list_repository_variables(self) -> Dict[str, str]:
        """
        List all repository variables.
        
        Returns:
            Dictionary of variable name -> value pairs
        """
        try:
            url = f"https://api.github.com/repos/{self.repo_name}/actions/variables"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                variables = {var['name']: var['value'] for var in data.get('variables', [])}
                self.logger.debug(f"Listed {len(variables)} repository variables")
                return variables
            else:
                self.logger.error(f"Failed to list repository variables: {response.status_code}")
                return {}
                
        except Exception as e:
            self.logger.error(f"Exception listing repository variables: {e}")
            return {}
    
    # ===== ENVIRONMENT VARIABLES (Environment-Specific) =====
    
    def get_environment_variable(self, env_name: str, var_name: str, default: str = "") -> str:
        """
        Get environment-specific variable value.
        
        Args:
            env_name: Environment name (e.g., 'production-social-media')
            var_name: Variable name
            default: Default value if variable not found
            
        Returns:
            Variable value or default
        """
        try:
            url = f"https://api.github.com/repos/{self.repo_name}/environments/{env_name}/variables/{var_name}"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                value = response.json().get('value', default)
                self.logger.debug(f"Retrieved environment variable {env_name}/{var_name}: {len(value)} chars")
                return value
            elif response.status_code == 404:
                self.logger.debug(f"Environment variable {env_name}/{var_name} not found")
                return default
            else:
                self.logger.error(f"Failed to get environment variable {env_name}/{var_name}: {response.status_code}")
                return default
                
        except Exception as e:
            self.logger.error(f"Exception getting environment variable {env_name}/{var_name}: {e}")
            return default
    
    def set_environment_variable(self, env_name: str, var_name: str, value: str) -> bool:
        """
        Set environment-specific variable value.
        
        Args:
            env_name: Environment name
            var_name: Variable name
            value: Variable value
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Try update first
            url = f"https://api.github.com/repos/{self.repo_name}/environments/{env_name}/variables/{var_name}"
            data = {"name": var_name, "value": value}
            
            response = requests.patch(url, headers=self.headers, json=data)
            
            if response.status_code == 204:
                self.logger.debug(f"✅ Updated environment variable {env_name}/{var_name}")
                return True
            elif response.status_code == 404:
                # Variable doesn't exist, create it
                url = f"https://api.github.com/repos/{self.repo_name}/environments/{env_name}/variables"
                response = requests.post(url, headers=self.headers, json=data)
                
                if response.status_code == 201:
                    self.logger.debug(f"✅ Created environment variable {env_name}/{var_name}")
                    return True
                else:
                    self.logger.error(f"❌ Failed to create environment variable {env_name}/{var_name}: {response.status_code}")
                    return False
            else:
                self.logger.error(f"❌ Failed to update environment variable {env_name}/{var_name}: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Exception setting environment variable {env_name}/{var_name}: {e}")
            return False
    
    # ===== SMART VARIABLE ACCESS (Environment-Aware) =====
    
    def get_variable(self, name: str, default: str = "") -> str:
        """
        Get variable with environment-aware fallback.
        
        Priority order:
        1. Current environment variable (if in environment context)
        2. Repository variable
        3. Default value
        
        Args:
            name: Variable name
            default: Default value
            
        Returns:
            Variable value or default
        """
        # If running in environment context, check environment variables first
        if self.current_environment and self.current_environment != 'default':
            env_value = self.get_environment_variable(self.current_environment, name)
            if env_value:
                self.logger.debug(f"Using environment variable {self.current_environment}/{name}")
                return env_value
        
        # Fallback to repository variable
        repo_value = self.get_repository_variable(name, default)
        if repo_value != default:
            self.logger.debug(f"Using repository variable {name}")
            return repo_value
        
        self.logger.debug(f"Using default value for {name}")
        return default
    
    def set_variable(self, name: str, value: str, prefer_environment: bool = True) -> bool:
        """
        Set variable with environment-aware logic.
        
        Args:
            name: Variable name
            value: Variable value
            prefer_environment: If True, set in current environment (if available)
            
        Returns:
            True if successful, False otherwise
        """
        # If in environment context and prefer_environment is True
        if (prefer_environment and 
            self.current_environment and 
            self.current_environment != 'default'):
            
            success = self.set_environment_variable(self.current_environment, name, value)
            if success:
                self.logger.debug(f"Set environment variable {self.current_environment}/{name}")
                return True
            else:
                self.logger.warning(f"Failed to set environment variable, falling back to repository")
        
        # Fallback to repository variable
        success = self.set_repository_variable(name, value)
        if success:
            self.logger.debug(f"Set repository variable {name}")
            return True
        
        self.logger.error(f"Failed to set variable {name} in any scope")
        return False
    
    # ===== DIAGNOSTICS AND DEBUGGING =====
    
    def diagnose_access(self, test_var_name: str = None) -> Dict[str, Any]:
        """
        Perform comprehensive access diagnostics.
        
        Args:
            test_var_name: Optional test variable name
            
        Returns:
            Diagnostic information dictionary
        """
        if not test_var_name:
            test_var_name = f"TEST_ACCESS_{int(__import__('time').time())}"
        
        diagnostics = {
            'environment': self.current_environment,
            'repo_name': self.repo_name,
            'read_token_available': bool(self.read_token),
            'write_token_available': bool(self.write_token),
            'tokens_different': self.read_token != self.write_token,
            'repository_access': False,
            'variable_read_test': False,
            'variable_write_test': False,
            'environment_access': False,
            'existing_variables': [],
            'errors': []
        }
        
        try:
            # Test repository access
            if self.read_repo:
                repo_info = self.read_repo.full_name
                diagnostics['repository_access'] = True
                diagnostics['repo_full_name'] = repo_info
            else:
                diagnostics['errors'].append('No repository read access available')
            
            # Test variable listing
            try:
                variables = self.list_repository_variables()
                diagnostics['existing_variables'] = list(variables.keys())
                diagnostics['variable_count'] = len(variables)
            except Exception as e:
                diagnostics['errors'].append(f'Cannot list variables: {e}')
            
            # Test variable write
            test_value = f"test_{int(__import__('time').time())}"
            if self.set_repository_variable(test_var_name, test_value):
                diagnostics['variable_write_test'] = True
                
                # Test variable read
                read_value = self.get_repository_variable(test_var_name)
                if read_value == test_value:
                    diagnostics['variable_read_test'] = True
                else:
                    diagnostics['errors'].append(f'Read value mismatch: {read_value} != {test_value}')
                
                # Cleanup test variable
                try:
                    url = f"https://api.github.com/repos/{self.repo_name}/actions/variables/{test_var_name}"
                    requests.delete(url, headers=self.headers)
                except:
                    pass  # Ignore cleanup errors
            else:
                diagnostics['errors'].append('Cannot write repository variables')
            
            # Test environment access (if in environment)
            if self.current_environment and self.current_environment != 'default':
                if self.set_environment_variable(self.current_environment, test_var_name, test_value):
                    diagnostics['environment_access'] = True
                    # Cleanup
                    try:
                        url = f"https://api.github.com/repos/{self.repo_name}/environments/{self.current_environment}/variables/{test_var_name}"
                        requests.delete(url, headers=self.headers)
                    except:
                        pass
        
        except Exception as e:
            diagnostics['errors'].append(f'Diagnostic exception: {e}')
        
        return diagnostics
    
    def print_diagnostics(self):
        """Print comprehensive diagnostic information."""
        diag = self.diagnose_access()
        
        print("\n" + "="*60)
        print("GITHUB VARIABLES DIAGNOSTICS")
        print("="*60)
        print(f"Repository: {diag['repo_name']}")
        print(f"Environment: {diag['environment']}")
        print(f"Read Token: {'[OK] Available' if diag['read_token_available'] else '[X] Missing'}")
        print(f"Write Token: {'[OK] Available' if diag['write_token_available'] else '[X] Missing'}")
        print(f"Different Tokens: {'[OK] Yes (PAT)' if diag['tokens_different'] else '[!] No (same token)'}")
        print()
        
        print("ACCESS TESTS:")
        print(f"Repository Access: {'[OK] Success' if diag['repository_access'] else '[X] Failed'}")
        print(f"Variable Read: {'[OK] Success' if diag['variable_read_test'] else '[X] Failed'}")
        print(f"Variable Write: {'[OK] Success' if diag['variable_write_test'] else '[X] Failed'}")
        print(f"Environment Access: {'[OK] Success' if diag['environment_access'] else '[X] Failed'}")
        print()
        
        if diag['existing_variables']:
            print(f"EXISTING VARIABLES ({diag['variable_count']}):")
            for var in diag['existing_variables'][:10]:  # Show first 10
                print(f"  - {var}")
            if diag['variable_count'] > 10:
                print(f"  ... and {diag['variable_count'] - 10} more")
            print()
        
        if diag['errors']:
            print("ERRORS:")
            for error in diag['errors']:
                print(f"  [X] {error}")
            print()
        
        print("="*60)


# ===== USAGE EXAMPLES =====

def example_basic_usage():
    """Example: Basic repository variables usage."""
    # Initialize manager
    manager = GitHubVariablesManager(
        repo_name="webmemo-code/flickr-to-instagram-automation",
        read_token=os.getenv('GITHUB_TOKEN'),
        write_token=os.getenv('PERSONAL_ACCESS_TOKEN')
    )
    
    # Set a variable
    success = manager.set_repository_variable("TEST_VAR", "test_value")
    print(f"Set variable: {success}")
    
    # Get a variable
    value = manager.get_repository_variable("TEST_VAR", "default")
    print(f"Got variable: {value}")
    
    # List all variables
    variables = manager.list_repository_variables()
    print(f"All variables: {list(variables.keys())}")


def example_environment_usage():
    """Example: Environment-specific variables."""
    manager = GitHubVariablesManager(
        repo_name="webmemo-code/flickr-to-instagram-automation",
        write_token=os.getenv('PERSONAL_ACCESS_TOKEN')
    )
    
    # Set environment-specific variable
    success = manager.set_environment_variable(
        env_name="production-social-media",
        var_name="ALBUM_POSITION",
        value="21"
    )
    print(f"Set environment variable: {success}")
    
    # Get environment-specific variable
    value = manager.get_environment_variable(
        env_name="production-social-media",
        var_name="ALBUM_POSITION",
        default="0"
    )
    print(f"Got environment variable: {value}")


def example_state_manager_integration():
    """Example: Integration with existing StateManager."""
    
    class EnhancedStateManager:
        def __init__(self, config, repo_name: str):
            self.config = config
            self.variables_manager = GitHubVariablesManager(
                repo_name=repo_name,
                read_token=config.github_token,
                write_token=os.getenv('PERSONAL_ACCESS_TOKEN', config.github_token)
            )
            self.current_album_id = config.flickr_album_id
            self.logger = logging.getLogger(__name__)
        
        def get_last_posted_position(self) -> int:
            """Get last posted position with environment awareness."""
            var_name = f"LAST_POSTED_POSITION_{self.current_album_id}"
            value = self.variables_manager.get_variable(var_name, "0")
            try:
                return int(value)
            except ValueError:
                self.logger.warning(f"Invalid position value: {value}")
                return 0
        
        def set_last_posted_position(self, position: int) -> bool:
            """Set last posted position."""
            var_name = f"LAST_POSTED_POSITION_{self.current_album_id}"
            return self.variables_manager.set_variable(var_name, str(position))
        
        def diagnose_system(self):
            """Run comprehensive system diagnostics."""
            print("\n" + "="*60)
            print("FLICKR-TO-INSTAGRAM STATE DIAGNOSTICS")
            print("="*60)
            
            # Check current state
            position = self.get_last_posted_position()
            print(f"Current Album ID: {self.current_album_id}")
            print(f"Last Posted Position: {position}")
            
            # Check environment
            env = os.getenv('GITHUB_ENV_NAME', 'default')
            print(f"Environment Context: {env}")
            
            # Run variable manager diagnostics
            self.variables_manager.print_diagnostics()
            
            # Check specific variables
            print("CURRENT STATE VARIABLES:")
            for var_type in ['LAST_POSTED_POSITION', 'TOTAL_ALBUM_PHOTOS', 'FAILED_POSITIONS', 'INSTAGRAM_POSTS']:
                var_name = f"{var_type}_{self.current_album_id}"
                value = self.variables_manager.get_variable(var_name, "NOT_FOUND")
                print(f"  {var_name}: {value[:100]}..." if len(value) > 100 else f"  {var_name}: {value}")


if __name__ == "__main__":
    """
    Run diagnostics and examples.
    
    Usage:
        python read_write_github_variables.py
    """
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("GitHub Variables Manager - Diagnostics & Examples")
    print("="*60)
    
    # Run diagnostics
    manager = GitHubVariablesManager(
        repo_name="webmemo-code/flickr-to-instagram-automation"
    )
    
    manager.print_diagnostics()
    
    # Run examples if tokens are available
    if os.getenv('PERSONAL_ACCESS_TOKEN'):
        print("\nRunning examples...")
        example_basic_usage()
        example_environment_usage()
    else:
        print("\n[!] Set PERSONAL_ACCESS_TOKEN environment variable to run write examples")