# GCP VM Manager

A Python application for managing Google Cloud VM instances with a GUI or command-line interface. Run directly from GitHub with zero setup using `uvx`.

## Overview

Control your GCP virtual machines with:
- **GUI Application**: Visual interface with persistent configuration (for end users)
- **Console Application**: Interactive command-line tool (for developers)
- **Service Account Authentication**: Secure GCP access
- **(almost) Zero Installation**: Run directly from GitHub using UV

## For Users (VM Control)

### Prerequisites
1. **Install UV** (if not already installed):
   ```bash
   # macOS/Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Windows (PowerShell)
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```
2. **Install git** (if not already installed):
   * [windows](https://git-scm.com/downloads/win)
   * [mac](https://git-scm.com/downloads/mac)
   * linux, use your package manager

4. Get a GCP service account JSON key file with VM management permissions

### Quick Start
**Windows Users:** Download and double-click [`start-gui.bat`](start-gui.bat) for one-click launch

**Command Line:**
```bash
# Run GUI application
uvx --from git+https://github.com/vanossj/gcp-vm-manager.git gcp-vm-manager-gui
```


### Setup
1. Launch the GUI (command above)
2. Click "Configure" button
3. Fill in:
   - GCP Project ID
   - Zone (e.g., `us-central1-a`)
   - VM Instance Name
   - Service Account Key File (use Browse button)
4. Click "Save" - settings persist between sessions


## For Developers (Project Development)

### Development Setup
```bash
# Clone repository
git clone https://github.com/vanossj/gcp-vm-manager.git
cd gcp-vm

# Install dependencies
uv sync

# Run locally
uv run gcp-vm-manager-gui     # GUI version
uv run gcp-vm-manager         # Console version
```

### Project Structure
```
gcp-vm/
├── gcp_vm_manager/
│   ├── main.py          # Core VM management logic
│   ├── gui.py           # PySide6 GUI application
│   └── __init__.py
├── start-gui.bat        # Windows double-click launcher
├── start-gui.sh         # Unix command-line launcher
├── pyproject.toml       # UV project configuration
├── .python-version      # Python 3.12
└── README.md
```

### Key Components
- **GCPVMManager**: Main class for VM operations
- **ConfigDialog**: GUI configuration interface
- **VMWorker**: Background thread for GUI operations
- **Persistent Config**: JSON storage in `~/.gcp-vm-manager/`

### Console Application (Development/Advanced)
For development and advanced use cases:
```bash
# Run console version
uvx --from git+https://github.com/vanossj/gcp-vm-manager.git gcp-vm-manager

# Or locally
uv run gcp-vm-manager
```

### Windows Launcher Scripts
- **`start-gui.bat`**: Double-click launcher for Windows users
- **`start-gui.sh`**: Command-line launcher for Unix systems

**Console Setup**: Set environment variables or the app will prompt you:
```bash
export GCP_PROJECT_ID="your-project-id"
export GCP_ZONE="us-central1-a"
export GCP_INSTANCE_NAME="your-vm-name"
export GCP_SERVICE_KEY_PATH="/path/to/service-account-key.json"
```

### Development Commands
```bash
uv sync                  # Install/update dependencies
uv run pytest           # Run tests (if added)
uv build                 # Build package
```

### GCP Service Account Setup
For development and user distribution:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. **IAM & Admin** > **Service Accounts**
3. Create service account with appropriate permissions (see below)
4. Generate and download JSON key file
5. Distribute key file to users securely

#### Minimum Required Permissions
The service account needs these specific permissions:
- `compute.instances.get` - Read VM status and details
- `compute.instances.start` - Start VM instances  
- `compute.instances.stop` - Stop VM instances

#### Recommended IAM Roles
**Option 1: Predefined Role (Simplest)**
- `roles/compute.instanceAdmin.v1` - Provides necessary permissions plus some extras

**Option 2: Custom Role (Most Secure)**
Create a custom role with only the minimum permissions above:
```json
{
  "title": "VM Manager Role",
  "description": "Minimal permissions for GCP VM Manager app",
  "includedPermissions": [
    "compute.instances.get",
    "compute.instances.start", 
    "compute.instances.stop"
  ]
}
```

**Option 3: Instance-Specific (Recommended for Production)**
Use IAM conditions to limit access to specific VM instances:
- Base role: Custom role above
- Condition: `resource.name == "projects/PROJECT_ID/zones/ZONE/instances/INSTANCE_NAME"`
