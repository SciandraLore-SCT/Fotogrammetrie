"""
Build script for creating standalone executables
Creates .exe for Windows and .app for macOS
"""

import PyInstaller.__main__
import sys
import platform
from pathlib import Path

def build_viewer_exe():
    """Build the 3D viewer executable"""
    
    system = platform.system()
    
    print("="*70)
    print("Building 3D Viewer Standalone Executable")
    print("="*70)
    print(f"Platform: {system}")
    print(f"Python: {sys.version}")
    
    # Common options
    common_args = [
        'viewer-glb-gui.py',
        '--name=3D_Viewer_Pro',
        '--onefile',
        '--windowed',  # No console window
        '--icon=icon.ico' if Path('icon.ico').exists() else '',
        
        # Include the viewer script
        '--add-data=viewer-glb.py:.',
        
        # Hidden imports (libraries not auto-detected)
        '--hidden-import=pyglet',
        '--hidden-import=pyglet.gl',
        '--hidden-import=pyglet.window',
        '--hidden-import=pyglet.graphics',
        '--hidden-import=pyglet.math',
        '--hidden-import=trimesh',
        '--hidden-import=numpy',
        '--hidden-import=customtkinter',
        '--hidden-import=PIL',
        '--hidden-import=PIL._tkinter_finder',
        
        # Cleanup
        '--clean',
        '--noconfirm',
    ]
    
    # Remove empty strings
    common_args = [arg for arg in common_args if arg]
    
    # Platform-specific
    if system == 'Windows':
        print("\nBuilding Windows executable...")
        PyInstaller.__main__.run(common_args)
        
    elif system == 'Darwin':  # macOS
        print("\nBuilding macOS application...")
        mac_args = common_args + [
            '--osx-bundle-identifier=com.3dviewer.pro',
        ]
        PyInstaller.__main__.run(mac_args)
    
    else:  # Linux
        print("\nBuilding Linux executable...")
        PyInstaller.__main__.run(common_args)
    
    print("\n" + "="*70)
    print("✓ Build complete!")
    print("="*70)
    print(f"\nExecutable location: dist/3D_Viewer_Pro{'.exe' if system=='Windows' else ''}")
    print("\nYou can distribute the entire 'dist' folder.")
    print("Users don't need Python installed!")


if __name__ == '__main__':
    try:
        build_viewer_exe()
    except Exception as e:
        print(f"\n✗ Build failed: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")