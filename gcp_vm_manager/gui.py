#!/usr/bin/env python3
"""
GCP VM Manager - GUI Application

A PySide6 GUI application to manage GCP VM instances using service account authentication.
Provides a visual interface with VM status display and control buttons.
"""

import os
import sys
import threading
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QGroupBox, QDialog, QFormLayout,
    QLineEdit, QFileDialog, QMessageBox, QProgressBar, QFrame
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QThread
from PySide6.QtGui import QFont, QIcon, QPalette

from .main import GCPVMManager, load_saved_config, save_config, validate_config, clear_saved_config, get_config_file_path


class VMWorker(QObject):
    """Worker thread for VM operations to prevent GUI freezing."""
    
    status_updated = Signal(str)
    operation_completed = Signal(bool, str)  # success, message
    error_occurred = Signal(str)
    
    def __init__(self, vm_manager: GCPVMManager):
        super().__init__()
        self.vm_manager = vm_manager
        
    def get_status(self):
        """Get VM status in background thread."""
        try:
            status = self.vm_manager.get_instance_status()
            if status:
                self.status_updated.emit(status)
            else:
                self.error_occurred.emit("Failed to get VM status")
        except Exception as e:
            self.error_occurred.emit(f"Error getting status: {str(e)}")
    
    def start_vm(self):
        """Start VM in background thread."""
        try:
            success = self.vm_manager.start_instance()
            if success:
                self.operation_completed.emit(True, "VM start operation initiated successfully")
            else:
                self.operation_completed.emit(False, "Failed to start VM")
        except Exception as e:
            self.error_occurred.emit(f"Error starting VM: {str(e)}")
    
    def stop_vm(self):
        """Stop VM in background thread."""
        try:
            success = self.vm_manager.stop_instance()
            if success:
                self.operation_completed.emit(True, "VM stop operation initiated successfully")
            else:
                self.operation_completed.emit(False, "Failed to stop VM")
        except Exception as e:
            self.error_occurred.emit(f"Error stopping VM: {str(e)}")


class ConfigDialog(QDialog):
    """Configuration dialog for VM settings."""
    
    def __init__(self, parent=None, config=None):
        super().__init__(parent)
        self.setWindowTitle("GCP VM Configuration")
        self.setModal(True)
        self.resize(500, 300)
        
        # Store config
        self.config = config or {}
        
        # Setup UI
        self.setup_ui()
        
        # Load existing config
        self.load_config()
    
    def setup_ui(self):
        """Setup the configuration dialog UI."""
        layout = QVBoxLayout(self)
        
        # Form layout
        form_layout = QFormLayout()
        
        # Input fields
        self.project_id_edit = QLineEdit()
        self.project_id_edit.setPlaceholderText("your-project-id")
        form_layout.addRow("GCP Project ID:", self.project_id_edit)
        
        self.zone_edit = QLineEdit()
        self.zone_edit.setPlaceholderText("us-central1-a")
        form_layout.addRow("GCP Zone:", self.zone_edit)
        
        self.instance_name_edit = QLineEdit()
        self.instance_name_edit.setPlaceholderText("your-vm-instance")
        form_layout.addRow("Instance Name:", self.instance_name_edit)
        
        # Service key file with browse button
        key_layout = QHBoxLayout()
        self.service_key_edit = QLineEdit()
        self.service_key_edit.setPlaceholderText("/path/to/service-account-key.json")
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_service_key)
        key_layout.addWidget(self.service_key_edit)
        key_layout.addWidget(browse_btn)
        form_layout.addRow("Service Key File:", key_layout)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_and_accept)
        save_btn.setDefault(True)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def browse_service_key(self):
        """Open file dialog to browse for service key file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Service Account Key File",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            self.service_key_edit.setText(file_path)
    
    def load_config(self):
        """Load existing configuration into the dialog."""
        self.project_id_edit.setText(self.config.get('project_id', ''))
        self.zone_edit.setText(self.config.get('zone', ''))
        self.instance_name_edit.setText(self.config.get('instance_name', ''))
        self.service_key_edit.setText(self.config.get('service_key_path', ''))
    
    def save_and_accept(self):
        """Save configuration and accept dialog."""
        config = self.get_config()
        if validate_config(config):
            if save_config(config):
                self.accept()
            else:
                QMessageBox.warning(self, "Save Error", "Failed to save configuration.")
        else:
            QMessageBox.warning(self, "Invalid Configuration", 
                              "Please fill in all required fields.")
    
    def get_config(self):
        """Get the configuration from the dialog."""
        return {
            'project_id': self.project_id_edit.text().strip(),
            'zone': self.zone_edit.text().strip(),
            'instance_name': self.instance_name_edit.text().strip(),
            'service_key_path': self.service_key_edit.text().strip()
        }


class GCPVMManagerGUI(QMainWindow):
    """Main GUI window for GCP VM Manager."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GCP VM Manager")
        self.setMinimumSize(600, 400)
        
        # Initialize variables
        self.vm_manager = None
        self.config = {}
        self.worker = None
        self.worker_thread = None
        
        # Setup UI
        self.setup_ui()
        
        # Setup timer for auto-refresh
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_status)
        
        # Load initial config
        self.load_initial_config()
    
    def setup_ui(self):
        """Setup the main window UI."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Title
        title_label = QLabel("🔧 GCP VM Manager")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # Configuration group
        config_group = QGroupBox("Configuration")
        config_layout = QVBoxLayout(config_group)
        
        self.config_label = QLabel("No configuration loaded")
        self.config_label.setWordWrap(True)
        config_layout.addWidget(self.config_label)
        
        config_btn_layout = QHBoxLayout()
        self.config_btn = QPushButton("⚙️ Configure")
        self.config_btn.clicked.connect(self.show_config_dialog)
        config_btn_layout.addWidget(self.config_btn)
        
        self.reset_config_btn = QPushButton("🗑️ Reset")
        self.reset_config_btn.clicked.connect(self.reset_config)
        self.reset_config_btn.setToolTip("Clear saved configuration")
        config_btn_layout.addWidget(self.reset_config_btn)
        
        config_btn_layout.addStretch()
        config_layout.addLayout(config_btn_layout)
        
        layout.addWidget(config_group)
        
        # VM Status group
        status_group = QGroupBox("VM Status")
        status_layout = QVBoxLayout(status_group)
        
        # Status display
        status_display_layout = QHBoxLayout()
        status_display_layout.addWidget(QLabel("Current Status:"))
        
        self.status_label = QLabel("Unknown")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        status_display_layout.addWidget(self.status_label)
        status_display_layout.addStretch()
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.refresh_status)
        status_display_layout.addWidget(self.refresh_btn)
        
        status_layout.addLayout(status_display_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)
        
        layout.addWidget(status_group)
        
        # Control buttons group
        control_group = QGroupBox("VM Controls")
        control_layout = QHBoxLayout(control_group)
        
        self.start_btn = QPushButton("🚀 Start VM")
        self.start_btn.clicked.connect(self.start_vm)
        self.start_btn.setEnabled(False)
        
        self.stop_btn = QPushButton("🛑 Stop VM")
        self.stop_btn.clicked.connect(self.stop_vm)
        self.stop_btn.setEnabled(False)
        
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        
        layout.addWidget(control_group)
        
        # Auto-refresh group
        refresh_group = QGroupBox("Auto-Refresh")
        refresh_layout = QHBoxLayout(refresh_group)
        
        self.auto_refresh_btn = QPushButton("▶️ Start Auto-Refresh (30s)")
        self.auto_refresh_btn.clicked.connect(self.toggle_auto_refresh)
        refresh_layout.addWidget(self.auto_refresh_btn)
        
        # Add cancel button for stopping operations
        self.cancel_btn = QPushButton("⏹️ Cancel")
        self.cancel_btn.clicked.connect(self.cancel_operations)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setToolTip("Cancel current operation")
        refresh_layout.addWidget(self.cancel_btn)
        
        refresh_layout.addStretch()
        
        layout.addWidget(refresh_group)
        
        # Log area
        log_group = QGroupBox("Activity Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_group)
        
        # Add stretch to push everything up
        layout.addStretch()
    
    def load_initial_config(self):
        """Load initial configuration from saved file, environment, or start with empty config."""
        try:
            # Load saved configuration first
            self.config = load_saved_config()
            
            # Override with environment variables if set
            import os
            if os.getenv('GCP_PROJECT_ID'):
                self.config['project_id'] = os.getenv('GCP_PROJECT_ID')
            if os.getenv('GCP_ZONE'):
                self.config['zone'] = os.getenv('GCP_ZONE')
            if os.getenv('GCP_INSTANCE_NAME'):
                self.config['instance_name'] = os.getenv('GCP_INSTANCE_NAME')
            if os.getenv('GCP_SERVICE_KEY_PATH'):
                self.config['service_key_path'] = os.getenv('GCP_SERVICE_KEY_PATH')
            
            if validate_config(self.config):
                self.update_config_display()
                self.initialize_vm_manager()
                self.log_message("✅ Configuration loaded successfully")
            else:
                self.update_config_display()
                self.log_message("⚠️ Configuration incomplete. Please configure the application using the Configure button.")
                
        except Exception as e:
            self.log_message(f"⚠️ Error loading configuration: {e}")
            self.config = {}
            self.update_config_display()
    
    def show_config_dialog(self):
        """Show the configuration dialog."""
        dialog = ConfigDialog(self, self.config)
        if dialog.exec() == QDialog.Accepted:
            new_config = dialog.get_config()
            self.config = new_config
            self.update_config_display()
            if validate_config(new_config):
                self.initialize_vm_manager()
                self.log_message("✅ Configuration saved and updated successfully")
            else:
                self.log_message("⚠️ Configuration saved but incomplete. Please fill in all required fields.")
    
    def reset_config(self):
        """Reset the configuration."""
        reply = QMessageBox.question(
            self, 
            "Reset Configuration", 
            "Are you sure you want to clear the saved configuration?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if clear_saved_config():
                self.config = {}
                self.vm_manager = None
                self.worker = None
                if self.worker_thread:
                    self.worker_thread.quit()
                    self.worker_thread.wait()
                    self.worker_thread = None
                
                self.update_config_display()
                self.status_label.setText("Unknown")
                self.status_label.setStyleSheet("font-weight: bold; font-size: 14px;")
                self.start_btn.setEnabled(False)
                self.stop_btn.setEnabled(False)
                self.log_message("✅ Configuration reset successfully")
            else:
                self.log_message("❌ Failed to reset configuration")
    
    def update_config_display(self):
        """Update the configuration display."""
        if not self.config:
            config_text = "No configuration loaded. Click Configure to set up."
        else:
            # Show partial config with indicators for missing values
            project = self.config.get('project_id', '❌ Not set')
            zone = self.config.get('zone', '❌ Not set')
            instance = self.config.get('instance_name', '❌ Not set')
            service_key = self.config.get('service_key_path', '❌ Not set')
            
            # Truncate service key path for display
            if service_key != '❌ Not set' and len(service_key) > 50:
                service_key = '...' + service_key[-47:]
            
            config_text = (
                f"Project: {project}\n"
                f"Zone: {zone}\n"
                f"Instance: {instance}\n"
                f"Service Key: {service_key}"
            )
        
        self.config_label.setText(config_text)
        
        # Add config file location in tooltip
        config_file = get_config_file_path()
        self.config_label.setToolTip(f"Configuration file: {config_file}")
    
    def initialize_vm_manager(self):
        """Initialize the VM manager with current configuration."""
        try:
            # Clear any existing worker to prevent conflicts
            if self.worker_thread:
                self.worker_thread.quit()
                self.worker_thread.wait()
                self.worker_thread = None
                self.worker = None
            
            self.vm_manager = GCPVMManager(
                project_id=self.config['project_id'],
                zone=self.config['zone'],
                instance_name=self.config['instance_name'],
                service_key_path=self.config['service_key_path']
            )
            
            # Test authentication
            self.log_message("🔐 Testing authentication...")
            if self.vm_manager.authenticate():
                self.log_message("✅ Successfully authenticated with GCP")
                self.setup_worker()
                # Don't automatically refresh - let user do it manually
                self.log_message("💡 Click 'Refresh' to check VM status")
            else:
                self.log_message("❌ Authentication failed - please check your service account key")
                self.vm_manager = None
                QMessageBox.warning(self, "Authentication Failed", 
                                   "Failed to authenticate with GCP.\n\n"
                                   "Please check:\n"
                                   "• Service account key file path\n"
                                   "• Key file permissions\n"
                                   "• Network connectivity")
        except Exception as e:
            self.log_message(f"❌ Error initializing VM manager: {e}")
            self.vm_manager = None
            QMessageBox.critical(self, "Initialization Error", 
                               f"Failed to initialize VM manager:\n{e}\n\n"
                               "Please check your configuration and try again.")
    
    def setup_worker(self):
        """Setup the worker thread for VM operations."""
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()
        
        self.worker_thread = QThread()
        self.worker = VMWorker(self.vm_manager)
        self.worker.moveToThread(self.worker_thread)
        
        # Connect signals
        self.worker.status_updated.connect(self.update_status)
        self.worker.operation_completed.connect(self.operation_completed)
        self.worker.error_occurred.connect(self.handle_error)
        
        self.worker_thread.start()
    
    def refresh_status(self):
        """Refresh the VM status."""
        if not self.worker or not self.vm_manager:
            self.log_message("⚠️ VM manager not initialized. Please configure the application first.")
            return
        
        self.show_progress("Checking VM status...")
        self.refresh_btn.setEnabled(False)
        
        # Use QTimer.singleShot to call worker method in the worker thread
        QTimer.singleShot(0, self.worker.get_status)
    
    def update_status(self, status: str):
        """Update the VM status display."""
        self.status_label.setText(status)
        self.hide_progress()
        self.refresh_btn.setEnabled(True)
        
        # Update button states based on status
        if status == "RUNNING":
            self.status_label.setStyleSheet("color: green; font-weight: bold; font-size: 14px;")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
        elif status == "TERMINATED":
            self.status_label.setStyleSheet("color: red; font-weight: bold; font-size: 14px;")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
        else:
            self.status_label.setStyleSheet("color: orange; font-weight: bold; font-size: 14px;")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
        
        self.log_message(f"📊 VM Status: {status}")
    
    def start_vm(self):
        """Start the VM."""
        if not self.worker:
            self.log_message("⚠️ VM manager not initialized. Please configure the application first.")
            return
        
        self.show_progress("Starting VM...")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        
        QTimer.singleShot(0, self.worker.start_vm)
    
    def stop_vm(self):
        """Stop the VM."""
        if not self.worker:
            self.log_message("⚠️ VM manager not initialized. Please configure the application first.")
            return
        
        self.show_progress("Stopping VM...")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        
        QTimer.singleShot(0, self.worker.stop_vm)
    
    def operation_completed(self, success: bool, message: str):
        """Handle completed VM operations."""
        self.hide_progress()
        
        if success:
            self.log_message(f"✅ {message}")
            # Refresh status after a short delay to see the change, but only if VM manager is working
            if self.vm_manager and self.worker:
                QTimer.singleShot(2000, self.refresh_status)
        else:
            self.log_message(f"❌ {message}")
            # Re-enable buttons without retrying
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
            self.refresh_btn.setEnabled(True)
    
    def handle_error(self, error_message: str):
        """Handle worker errors."""
        self.hide_progress()
        self.log_message(f"❌ {error_message}")
        
        # Don't show error dialog for every failed operation to prevent spam
        if "authentication" in error_message.lower() or "connection" in error_message.lower():
            QMessageBox.warning(self, "Connection Error", 
                              f"{error_message}\n\n"
                              "Please check your configuration and network connection.")
        
        # Re-enable buttons without retrying
        self.refresh_btn.setEnabled(True)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("Error")
        self.status_label.setStyleSheet("color: red; font-weight: bold; font-size: 14px;")
    
    def toggle_auto_refresh(self):
        """Toggle auto-refresh timer."""
        if self.refresh_timer.isActive():
            self.refresh_timer.stop()
            self.auto_refresh_btn.setText("▶️ Start Auto-Refresh (30s)")
            self.log_message("⏸️ Auto-refresh stopped")
        else:
            self.refresh_timer.start(30000)  # 30 seconds
            self.auto_refresh_btn.setText("⏸️ Stop Auto-Refresh")
            self.log_message("▶️ Auto-refresh started (30 second interval)")
    
    def show_progress(self, message: str):
        """Show progress bar with message."""
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.cancel_btn.setEnabled(True)
        self.log_message(f"⏳ {message}")
    
    def hide_progress(self):
        """Hide progress bar."""
        self.progress_bar.setVisible(False)
        self.cancel_btn.setEnabled(False)
    
    def cancel_operations(self):
        """Cancel current operations and reset the interface."""
        self.log_message("🛑 Cancelling operations...")
        
        # Stop auto-refresh if running
        if self.refresh_timer.isActive():
            self.refresh_timer.stop()
            self.auto_refresh_btn.setText("▶️ Start Auto-Refresh (30s)")
        
        # Clean up worker thread
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()
            self.worker_thread = None
            self.worker = None
        
        # Reset UI state
        self.hide_progress()
        self.refresh_btn.setEnabled(True)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("Cancelled")
        self.status_label.setStyleSheet("color: orange; font-weight: bold; font-size: 14px;")
        
        self.log_message("✅ Operations cancelled - click Refresh to try again")
    
    def log_message(self, message: str):
        """Add a message to the log."""
        self.log_text.append(message)
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def closeEvent(self, event):
        """Handle application close event."""
        # Stop timer
        if self.refresh_timer.isActive():
            self.refresh_timer.stop()
        
        # Clean up worker thread
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()
        
        event.accept()


def main():
    """Main entry point for the GUI application."""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("GCP VM Manager")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("GCP VM Manager")
    
    # Create and show main window
    window = GCPVMManagerGUI()
    window.show()
    
    # Start event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
