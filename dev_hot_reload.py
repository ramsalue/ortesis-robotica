"""
Hot-Reload Development Script for GUI Development
Automatically restarts the application when Python files change.

Installation:
    pip install watchdog

Usage:
    python dev_hot_reload.py
    
Then edit your GUI files and see changes instantly!
"""

import sys
import time
import subprocess
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class HotReloadHandler(FileSystemEventHandler):
    """Handles file change events and triggers app restart."""
    
    def __init__(self, script_path):
        self.script_path = script_path
        self.process = None
        self.last_restart = 0
        self.debounce_seconds = 1  # Prevent multiple restarts
        self.start_app()
    
    def start_app(self):
        """Start the PyQt application."""
        if self.process:
            self.process.terminate()
            self.process.wait()
        
        print("\n" + "="*60)
        print("🚀 Starting application...")
        print("="*60 + "\n")
        
        # Start app in new process
        self.process = subprocess.Popen(
            [sys.executable, self.script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    
    def on_modified(self, event):
        """Called when a file is modified."""
        # Only react to Python files
        if not event.src_path.endswith('.py'):
            return
        
        # Skip __pycache__ and temp files
        if '__pycache__' in event.src_path or event.src_path.endswith('.pyc'):
            return
        
        # Debounce rapid changes
        current_time = time.time()
        if current_time - self.last_restart < self.debounce_seconds:
            return
        
        self.last_restart = current_time
        
        print("\n" + "="*60)
        print(f"🔄 File changed: {Path(event.src_path).name}")
        print("   Reloading application...")
        print("="*60 + "\n")
        
        self.start_app()
    
    def stop(self):
        """Clean up before exit."""
        if self.process:
            self.process.terminate()
            self.process.wait()


def main():
    """Main entry point for hot-reload development."""
    
    # The main script to watch and run
    MAIN_SCRIPT = "rehabilitation_app.py"  # Change this if needed
    
    # Check if main script exists
    if not Path(MAIN_SCRIPT).exists():
        print(f"❌ Error: {MAIN_SCRIPT} not found!")
        print(f"   Make sure you're in the correct directory.")
        return
    
    print("="*60)
    print("🔥 HOT-RELOAD DEVELOPMENT MODE")
    print("="*60)
    print(f"📁 Watching: {Path.cwd()}")
    print(f"🎯 Main script: {MAIN_SCRIPT}")
    print("\n💡 Tips:")
    print("   - Edit any .py file and save")
    print("   - App will restart automatically")
    print("   - Press Ctrl+C to stop")
    print("="*60 + "\n")
    
    # Setup file watcher
    event_handler = HotReloadHandler(MAIN_SCRIPT)
    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=True)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n" + "="*60)
        print("🛑 Stopping hot-reload...")
        print("="*60)
        observer.stop()
        event_handler.stop()
    
    observer.join()
    print("\n✅ Hot-reload stopped. Goodbye!\n")


if __name__ == "__main__":
    main()
