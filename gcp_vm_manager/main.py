#!/usr/bin/env python3
"""
GCP VM Manager - Main Application

A Python application to manage GCP VM instances using service account authentication.
Provides an interactive menu to start, stop, or leave VMs unchanged based on their current state.
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any

from google.cloud import compute_v1
from google.oauth2 import service_account
from google.auth.exceptions import DefaultCredentialsError
import google.auth.exceptions


class GCPVMManager:
    """Manages GCP VM instances with service account authentication."""
    
    def __init__(self, project_id: str, zone: str, instance_name: str, service_key_path: str):
        """
        Initialize the GCP VM Manager.
        
        Args:
            project_id: GCP Project ID
            zone: GCP Zone (e.g., 'us-central1-a')
            instance_name: Name of the VM instance
            service_key_path: Path to the service account JSON key file
        """
        self.project_id = project_id
        self.zone = zone
        self.instance_name = instance_name
        self.service_key_path = service_key_path
        self.compute_client = None
        
    def authenticate(self) -> bool:
        """
        Authenticate using the service account key file.
        
        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            # Check if service key file exists
            if not Path(self.service_key_path).exists():
                print(f"❌ Error: Service account key file not found: {self.service_key_path}")
                return False
            
            # Load credentials from service account key file
            credentials = service_account.Credentials.from_service_account_file(
                self.service_key_path,
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
            
            # Initialize the compute client with credentials
            self.compute_client = compute_v1.InstancesClient(credentials=credentials)
            
            print("✅ Successfully authenticated with service account")
            return True
            
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            return False
    
    def get_instance_status(self) -> Optional[str]:
        """
        Get the current status of the VM instance.
        
        Returns:
            str: The instance status (RUNNING, TERMINATED, etc.) or None if error
        """
        try:
            request = compute_v1.GetInstanceRequest(
                project=self.project_id,
                zone=self.zone,
                instance=self.instance_name
            )
            instance = self.compute_client.get(request=request)
            return instance.status
            
        except Exception as e:
            print(f"❌ Error getting instance status: {e}")
            return None
    
    def start_instance(self) -> bool:
        """
        Start the VM instance.
        
        Returns:
            bool: True if operation started successfully, False otherwise
        """
        try:
            print(f"🚀 Starting instance '{self.instance_name}'...")
            request = compute_v1.StartInstanceRequest(
                project=self.project_id,
                zone=self.zone,
                instance=self.instance_name
            )
            operation = self.compute_client.start(request=request)
            print(f"✅ Start operation initiated successfully: {operation.name}")
            print("⏳ The instance is starting up (this may take a few moments)")
            return True
            
        except Exception as e:
            print(f"❌ Error starting instance: {e}")
            return False
    
    def stop_instance(self) -> bool:
        """
        Stop the VM instance.
        
        Returns:
            bool: True if operation started successfully, False otherwise
        """
        try:
            print(f"🛑 Stopping instance '{self.instance_name}'...")
            request = compute_v1.StopInstanceRequest(
                project=self.project_id,
                zone=self.zone,
                instance=self.instance_name
            )
            operation = self.compute_client.stop(request=request)
            print(f"✅ Stop operation initiated successfully: {operation.name}")
            print("⏳ The instance is shutting down (this may take a few moments)")
            return True
            
        except Exception as e:
            print(f"❌ Error stopping instance: {e}")
            return False


def get_config_file_path() -> Path:
    """
    Get the path to the configuration file.
    
    Returns:
        Path: Path to the configuration file
    """
    # Use user's home directory for config file
    config_dir = Path.home() / '.gcp-vm-manager'
    config_dir.mkdir(exist_ok=True)
    return config_dir / 'config.json'


def save_config(config: Dict[str, Any]) -> bool:
    """
    Save configuration to persistent storage.
    
    Args:
        config: Configuration dictionary to save
        
    Returns:
        bool: True if saved successfully, False otherwise
    """
    try:
        config_file = get_config_file_path()
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"✅ Configuration saved to: {config_file}")
        return True
    except Exception as e:
        print(f"❌ Error saving configuration: {e}")
        return False


def clear_saved_config() -> bool:
    """
    Clear the saved configuration file.
    
    Returns:
        bool: True if cleared successfully, False otherwise
    """
    try:
        config_file = get_config_file_path()
        if config_file.exists():
            config_file.unlink()
            print(f"✅ Configuration cleared: {config_file}")
        return True
    except Exception as e:
        print(f"❌ Error clearing configuration: {e}")
        return False


def load_saved_config() -> Dict[str, Any]:
    """
    Load configuration from persistent storage.
    
    Returns:
        dict: Configuration dictionary (empty if no saved config)
    """
    try:
        config_file = get_config_file_path()
        if config_file.exists():
            with open(config_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️ Error loading saved configuration: {e}")
    
    return {}


def load_config() -> dict:
    """
    Load configuration from various sources in priority order:
    1. Saved configuration file
    2. Environment variables
    3. User prompts (for console application)
    
    Returns:
        dict: Configuration dictionary
    """
    config = {}
    
    # Try to load from saved configuration first
    saved_config = load_saved_config()
    if saved_config:
        config.update(saved_config)
    
    # Override with environment variables if set
    if os.getenv('GCP_PROJECT_ID'):
        config['project_id'] = os.getenv('GCP_PROJECT_ID')
    if os.getenv('GCP_ZONE'):
        config['zone'] = os.getenv('GCP_ZONE')
    if os.getenv('GCP_INSTANCE_NAME'):
        config['instance_name'] = os.getenv('GCP_INSTANCE_NAME')
    if os.getenv('GCP_SERVICE_KEY_PATH'):
        config['service_key_path'] = os.getenv('GCP_SERVICE_KEY_PATH')
    
    # For console application, prompt for missing values
    # GUI application will handle missing values differently
    if not config.get('project_id'):
        config['project_id'] = input("Enter GCP Project ID: ").strip()
    
    if not config.get('zone'):
        config['zone'] = input("Enter GCP Zone (e.g., us-central1-a): ").strip()
    
    if not config.get('instance_name'):
        config['instance_name'] = input("Enter VM Instance Name: ").strip()
    
    if not config.get('service_key_path'):
        config['service_key_path'] = input("Enter path to service account key file: ").strip()
    
    return config


def validate_config(config: dict) -> bool:
    """
    Validate the configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        bool: True if configuration is valid, False otherwise
    """
    required_fields = ['project_id', 'zone', 'instance_name', 'service_key_path']
    
    for field in required_fields:
        if not config.get(field):
            print(f"❌ Error: {field} is required")
            return False
    
    return True


def display_menu(vm_status: str) -> None:
    """
    Display the interactive menu based on VM status.
    
    Args:
        vm_status: Current VM status
    """
    print("\n" + "="*50)
    print("🔧 GCP VM Manager - Action Menu")
    print("="*50)
    print(f"VM Status: {vm_status}")
    print()
    
    if vm_status == "RUNNING":
        print("📋 Available Actions:")
        print("1. 🛑 Stop the VM")
        print("2. ⏸️  Do nothing")
    elif vm_status == "TERMINATED":
        print("📋 Available Actions:")
        print("1. 🚀 Start the VM")
        print("2. ⏸️  Do nothing")
    else:
        print("📋 Available Actions:")
        print("1. 🚀 Try to start the VM")
        print("2. 🛑 Try to stop the VM")
        print("3. ⏸️  Do nothing")


def get_user_choice(vm_status: str) -> str:
    """
    Get user choice from the menu.
    
    Args:
        vm_status: Current VM status
        
    Returns:
        str: User choice ('start', 'stop', 'nothing')
    """
    while True:
        try:
            if vm_status in ["RUNNING", "TERMINATED"]:
                choice = input("\nEnter your choice (1-2): ").strip()
                if choice == "1":
                    return "stop" if vm_status == "RUNNING" else "start"
                elif choice == "2":
                    return "nothing"
                else:
                    print("❌ Invalid choice. Please enter 1 or 2.")
            else:
                choice = input("\nEnter your choice (1-3): ").strip()
                if choice == "1":
                    return "start"
                elif choice == "2":
                    return "stop"
                elif choice == "3":
                    return "nothing"
                else:
                    print("❌ Invalid choice. Please enter 1, 2, or 3.")
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            sys.exit(0)


def main():
    """Main application entry point."""
    print("🔧 GCP VM Manager")
    print("="*30)
    
    # Load configuration
    config = load_config()
    
    # Validate configuration
    if not validate_config(config):
        print("❌ Configuration validation failed. Exiting.")
        sys.exit(1)
    
    # Initialize VM manager
    vm_manager = GCPVMManager(
        project_id=config['project_id'],
        zone=config['zone'],
        instance_name=config['instance_name'],
        service_key_path=config['service_key_path']
    )
    
    # Authenticate
    if not vm_manager.authenticate():
        print("❌ Authentication failed. Exiting.")
        sys.exit(1)
    
    # Get VM status
    print(f"\n🔍 Checking status of VM '{config['instance_name']}' in zone '{config['zone']}'...")
    vm_status = vm_manager.get_instance_status()
    
    if vm_status is None:
        print("❌ Failed to get VM status. Exiting.")
        sys.exit(1)
    
    # Display menu and get user choice
    display_menu(vm_status)
    choice = get_user_choice(vm_status)
    
    # Execute user choice
    print("\n" + "="*50)
    if choice == "start":
        success = vm_manager.start_instance()
        if success:
            print("🎉 VM start operation completed successfully!")
        else:
            print("❌ Failed to start VM.")
    elif choice == "stop":
        success = vm_manager.stop_instance()
        if success:
            print("🎉 VM stop operation completed successfully!")
        else:
            print("❌ Failed to stop VM.")
    else:
        print("⏸️  No action taken. VM state unchanged.")
    
    print("\n👋 Thank you for using GCP VM Manager!")


if __name__ == "__main__":
    main()
