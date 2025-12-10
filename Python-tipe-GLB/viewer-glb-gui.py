"""
3D Model Viewer - Professional GUI (Enhanced)
CustomTkinter version with integrated terminal and better layout
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import subprocess
import sys
import json
import threading
from pathlib import Path
from datetime import datetime
import trimesh
import os
import queue

# Set appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class InteractiveTerminal(ctk.CTkToplevel):
    """Interactive terminal window with input capability"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Interactive Terminal")
        self.geometry("900x600")
        
        # Terminal output
        self.terminal = ctk.CTkTextbox(
            self, 
            wrap="word", 
            font=("Consolas", 11),
            fg_color="#1a1a1a"
        )
        self.terminal.pack(fill="both", expand=True, padx=10, pady=(10, 5))
        
        # Input frame
        input_frame = ctk.CTkFrame(self)
        input_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkLabel(
            input_frame,
            text="$",
            font=("Consolas", 12, "bold"),
            text_color="#4CAF50"
        ).pack(side="left", padx=(5, 5))
        
        self.input_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Enter command...",
            font=("Consolas", 11)
        )
        self.input_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.input_entry.bind("<Return>", self.execute_command)
        
        ctk.CTkButton(
            input_frame,
            text="Execute",
            command=lambda: self.execute_command(None),
            width=100
        ).pack(side="right", padx=5)
        
        # Bottom buttons
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkButton(
            btn_frame,
            text="Clear",
            command=self.clear,
            width=100
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text="Copy All",
            command=self.copy_all,
            width=100
        ).pack(side="left", padx=5)
        
        # Process tracking
        self.current_process = None
        
        # Don't close on X, just hide
        self.protocol("WM_DELETE_WINDOW", self.hide_window)
        
        self.log("Terminal ready. Type commands or run scripts.", "#4CAF50")
    
    def log(self, message, color="#E0E0E0"):
        """Add message to terminal"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.terminal.insert("end", f"[{timestamp}] {message}\n")
        
        # Get the line that was just inserted
        line_start = self.terminal.index("end-2l linestart")
        line_end = self.terminal.index("end-2l lineend")
        
        # Create unique tag for this line
        tag = f"line_{timestamp}_{len(message)}"
        self.terminal.tag_add(tag, line_start, line_end)
        self.terminal.tag_config(tag, foreground=color)
        
        # Auto-scroll
        self.terminal.see("end")
    
    def execute_command(self, event):
        """Execute command from input"""
        command = self.input_entry.get().strip()
        if not command:
            return
        
        self.log(f"$ {command}", "#4CAF50")
        self.input_entry.delete(0, "end")
        
        try:
            # Execute command
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Show output
            if result.stdout:
                self.log(result.stdout.strip(), "#E0E0E0")
            if result.stderr:
                self.log(result.stderr.strip(), "#EF5350")
            
            if result.returncode == 0:
                self.log(f"✓ Command completed (exit code: 0)", "#81C784")
            else:
                self.log(f"✗ Command failed (exit code: {result.returncode})", "#EF5350")
                
        except subprocess.TimeoutExpired:
            self.log("✗ Command timeout (30s limit)", "#FF9800")
        except Exception as e:
            self.log(f"✗ Error: {str(e)}", "#EF5350")
    
    def clear(self):
        """Clear terminal"""
        self.terminal.delete("1.0", "end")
        self.log("Terminal cleared.", "#4CAF50")
    
    def copy_all(self):
        """Copy all text to clipboard"""
        text = self.terminal.get("1.0", "end")
        self.clipboard_clear()
        self.clipboard_append(text)
        self.log("✓ Copied to clipboard", "#4CAF50")
    
    def hide_window(self):
        """Hide instead of closing"""
        self.withdraw()


class ViewerTerminal(ctk.CTkToplevel):
    """Real-time viewer process terminal"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Viewer Terminal Output")
        self.geometry("900x600")
        
        # Terminal output
        self.terminal = ctk.CTkTextbox(
            self,
            wrap="word",
            font=("Consolas", 11),
            fg_color="#1a1a1a"
        )
        self.terminal.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Bottom buttons
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkButton(
            btn_frame,
            text="Clear",
            command=self.clear,
            width=100
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text="Copy All",
            command=self.copy_all,
            width=100
        ).pack(side="right", padx=5)
        
        self.process = None
        self.protocol("WM_DELETE_WINDOW", self.hide_window)
        
    def log(self, message, color="#E0E0E0"):
        """Add message to terminal"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.terminal.insert("end", f"[{timestamp}] {message}\n")
        
        line_start = self.terminal.index("end-2l linestart")
        line_end = self.terminal.index("end-2l lineend")
        tag = f"line_{timestamp}"
        self.terminal.tag_add(tag, line_start, line_end)
        self.terminal.tag_config(tag, foreground=color)
        
        self.terminal.see("end")
    
    def clear(self):
        """Clear terminal"""
        self.terminal.delete("1.0", "end")
    
    def copy_all(self):
        """Copy all text to clipboard"""
        text = self.terminal.get("1.0", "end")
        self.clipboard_clear()
        self.clipboard_append(text)
    
    def hide_window(self):
        """Hide instead of closing"""
        self.withdraw()


class ViewerGUI(ctk.CTk):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        # Window config
        self.title("3D Model Viewer Pro")
        self.geometry("1000x750")
        self.minsize(800, 600)
        self.maxsize(1600, 1200)
        self.resizable(True, True)
                
        # Variables
        self.model_path = ctk.StringVar()
        self.texture_path = ctk.StringVar()
        self.output_path = ctk.StringVar()
        self.rotation_offset = ctk.DoubleVar(value=0.0)
        
        # Config
        self.config_file = Path.home() / ".3d_viewer_config.json"
        self.recent_files = []
        
        # Terminals
        self.interactive_terminal = InteractiveTerminal(self)
        self.interactive_terminal.withdraw()
        
        self.viewer_terminal = ViewerTerminal(self)
        self.viewer_terminal.withdraw()
        
        # Current viewer process
        self.viewer_process = None
        
        # Load config
        self.load_config()
        
        # Create UI
        self.create_ui()
        
        self.viewer_terminal.log("Application started", "#4CAF50")
    
    def create_ui(self):
        """Create main interface"""
        
        # === HEADER ===
        header = ctk.CTkFrame(self, corner_radius=0)
        header.pack(fill="x", pady=(0, 20))
        
        title = ctk.CTkLabel(
            header,
            text="🎨 3D Model Viewer Pro",
            font=ctk.CTkFont(size=32, weight="bold")
        )
        title.pack(pady=(20, 5))
        
        subtitle = ctk.CTkLabel(
            header,
            text="Professional viewer for GLB, OBJ, GLTF with advanced features",
            font=ctk.CTkFont(size=13),
            text_color="#B0BEC5"
        )
        subtitle.pack()
        
        # === MAIN CONTENT ===
        content = ctk.CTkFrame(self)
        content.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Tabs
        tabview = ctk.CTkTabview(content)
        tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create tabs
        tab_viewer = tabview.add("🖥️ Viewer")
        tab_converter = tabview.add("🔄 OBJ → GLB")
        tab_settings = tabview.add("⚙️ Settings")
        tab_credits = tabview.add("👥 Credits")
        
        # === TABS ===
        self.create_viewer_tab(tab_viewer)
        self.create_converter_tab(tab_converter)
        self.create_settings_tab(tab_settings)
        self.create_credits_tab(tab_credits)
        # Update layout on window resize
        self.bind("<Configure>", lambda e: self.after(100, self.update_layout_sizes))
        
        # === FOOTER ===
        footer = ctk.CTkFrame(self, height=50, corner_radius=0)
        footer.pack(fill="x", side="bottom")
        
        # Terminal buttons
        ctk.CTkButton(
            footer,
            text="💻 Terminal",
            command=self.toggle_interactive_terminal,
            width=130,
            height=35
        ).pack(side="left", padx=(20, 5), pady=10)
        
        ctk.CTkButton(
            footer,
            text="📺 Viewer Output",
            command=self.toggle_viewer_terminal,
            width=130,
            height=35
        ).pack(side="left", padx=5, pady=10)
        
        # Status label
        self.status_label = ctk.CTkLabel(
            footer,
            text="Ready",
            font=ctk.CTkFont(size=12),
            text_color="#81C784"
        )
        self.status_label.pack(side="right", padx=20)
    
    def create_viewer_tab(self, parent):
        """Create viewer tab content"""
        
        # Model file section
        model_frame = ctk.CTkFrame(parent)
        model_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(
            model_frame,
            text="3D Model File",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        model_input_frame = ctk.CTkFrame(model_frame)
        model_input_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.model_entry = ctk.CTkEntry(
            model_input_frame,
            textvariable=self.model_path,
            placeholder_text="Select GLB, OBJ or GLTF file...",
            height=40
        )
        self.model_entry.pack(side="left", fill="x", expand=True, padx=(5, 5))
        
        ctk.CTkButton(
            model_input_frame,
            text="📁 Browse",
            command=self.browse_model,
            width=120,
            height=40
        ).pack(side="right", padx=(0, 5))
        
        # Texture file section
        texture_frame = ctk.CTkFrame(parent)
        texture_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            texture_frame,
            text="Texture File (Optional)",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        texture_input_frame = ctk.CTkFrame(texture_frame)
        texture_input_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.texture_entry = ctk.CTkEntry(
            texture_input_frame,
            textvariable=self.texture_path,
            placeholder_text="Optional: PNG, JPG, WEBP...",
            height=40
        )
        self.texture_entry.pack(side="left", fill="x", expand=True, padx=(5, 5))
        
        ctk.CTkButton(
            texture_input_frame,
            text="📁 Browse",
            command=self.browse_texture,
            width=120,
            height=40
        ).pack(side="right", padx=(0, 5))
        
        # Rotation control
        rotation_frame = ctk.CTkFrame(parent)
        rotation_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            rotation_frame,
            text="Grid Rotation Offset (degrees)",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        rot_control_frame = ctk.CTkFrame(rotation_frame)
        rot_control_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.rotation_slider = ctk.CTkSlider(
            rot_control_frame,
            from_=0,
            to=360,
            variable=self.rotation_offset,
            width=400
        )
        self.rotation_slider.pack(side="left", padx=5, fill="x", expand=True)
        
        self.rotation_label = ctk.CTkLabel(
            rot_control_frame,
            text="0°",
            width=50
        )
        self.rotation_label.pack(side="right", padx=5)
        
        self.rotation_slider.configure(command=self.update_rotation_label)
        
        # Launch button (BIG!)
        launch_frame = ctk.CTkFrame(parent)
        launch_frame.pack(fill="x", padx=20, pady=20)
        
        self.launch_btn = ctk.CTkButton(
            launch_frame,
            text="🚀 LAUNCH VIEWER",
            command=self.launch_viewer,
            font=ctk.CTkFont(size=18, weight="bold"),
            height=60,
            fg_color="#2E7D32",
            hover_color="#1B5E20"
        )
        self.launch_btn.pack(fill="x", padx=10, pady=10)
        
        # Recent files - BIGGER!
        recent_frame = ctk.CTkFrame(parent)
        recent_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        ctk.CTkLabel(
            recent_frame,
            text="Recent Files",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        # Scrollable frame for recent files - TALLER!
        self.recent_scroll = ctk.CTkScrollableFrame(recent_frame, height=200)
        self.recent_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        self.update_recent_files()
    
    def create_converter_tab(self, parent):
        """Create OBJ to GLB converter tab"""
        
        # Info
        info_frame = ctk.CTkFrame(parent)
        info_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(
            info_frame,
            text="⚡ OBJ → GLB Converter",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(10, 5))
        
        ctk.CTkLabel(
            info_frame,
            text="Convert OBJ files to GLB format for faster loading (5-7x speedup!)",
            font=ctk.CTkFont(size=12),
            text_color="#B0BEC5"
        ).pack(pady=(0, 10))
        
        # Input OBJ
        input_frame = ctk.CTkFrame(parent)
        input_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            input_frame,
            text="Input OBJ File",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        input_entry_frame = ctk.CTkFrame(input_frame)
        input_entry_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.conv_input = ctk.CTkEntry(
            input_entry_frame,
            placeholder_text="Select OBJ file to convert...",
            height=40
        )
        self.conv_input.pack(side="left", fill="x", expand=True, padx=(5, 5))
        
        ctk.CTkButton(
            input_entry_frame,
            text="📁 Browse",
            command=self.browse_convert_input,
            width=120,
            height=40
        ).pack(side="right", padx=(0, 5))
        
        # Output GLB
        output_frame = ctk.CTkFrame(parent)
        output_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            output_frame,
            text="Output GLB File",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        output_entry_frame = ctk.CTkFrame(output_frame)
        output_entry_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.conv_output = ctk.CTkEntry(
            output_entry_frame,
            textvariable=self.output_path,
            placeholder_text="Output path (auto-filled)...",
            height=40
        )
        self.conv_output.pack(side="left", fill="x", expand=True, padx=(5, 5))
        
        ctk.CTkButton(
            output_entry_frame,
            text="📁 Browse",
            command=self.browse_convert_output,
            width=120,
            height=40
        ).pack(side="right", padx=(0, 5))
        
        # Progress
        self.progress_label = ctk.CTkLabel(
            parent,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#FFB74D"
        )
        self.progress_label.pack(pady=10)
        
        self.progress_bar = ctk.CTkProgressBar(parent, width=500)
        self.progress_bar.pack(pady=5)
        self.progress_bar.set(0)
        
        # Convert button
        convert_btn = ctk.CTkButton(
            parent,
            text="🔄 CONVERT TO GLB",
            command=self.convert_obj_to_glb,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            width=300,
            fg_color="#1976D2",
            hover_color="#0D47A1"
        )
        convert_btn.pack(pady=20)
    
    def create_settings_tab(self, parent):
        """Create settings tab"""
        
        # Appearance
        appearance_frame = ctk.CTkFrame(parent)
        appearance_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(
            appearance_frame,
            text="Appearance",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        theme_frame = ctk.CTkFrame(appearance_frame)
        theme_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkLabel(theme_frame, text="Theme:").pack(side="left", padx=(5, 10))
        
        self.theme_menu = ctk.CTkOptionMenu(
            theme_frame,
            values=["Dark", "Light", "System"],
            command=self.change_theme,
            width=150
        )
        self.theme_menu.pack(side="left", padx=5)
        self.theme_menu.set("Dark")
        
        # Viewer path
        viewer_frame = ctk.CTkFrame(parent)
        viewer_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            viewer_frame,
            text="Viewer Script Path",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        viewer_path_frame = ctk.CTkFrame(viewer_frame)
        viewer_path_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.viewer_path_entry = ctk.CTkEntry(
            viewer_path_frame,
            placeholder_text="viewer-glb.py"
        )
        self.viewer_path_entry.pack(side="left", fill="x", expand=True, padx=(5, 5))
        self.viewer_path_entry.insert(0, "viewer-glb.py")
        
        # About
        about_frame = ctk.CTkFrame(parent)
        about_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        ctk.CTkLabel(
            about_frame,
            text="About",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        about_text = """
3D Model Viewer Pro v1.5

Features:
• Fast GLB/GLTF viewer (5-7x faster than OBJ)
• OBJ format support with texture loading
• Built-in OBJ to GLB converter
• Professional OpenGL rendering
• Interactive controls (rotate, zoom, pan)
• Grid rotation offset control
• Real-time viewer terminal output
• Interactive command terminal
• Recent files with larger display

Created for non-programmers
Easy to use, powerful features
        """
        
        ctk.CTkLabel(
            about_frame,
            text=about_text,
            font=ctk.CTkFont(size=11),
            justify="left",
            text_color="#B0BEC5"
        ).pack(anchor="w", padx=20, pady=10)
    
    def create_credits_tab(self, parent):
        """Create credits tab"""
        
        # Main frame
        credits_frame = ctk.CTkFrame(parent)
        credits_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        ctk.CTkLabel(
            credits_frame,
            text="👥 Credits & Contributors",
            font=ctk.CTkFont(size=24, weight="bold")
        ).pack(pady=(20, 30))
        
        # Scrollable content
        scroll_frame = ctk.CTkScrollableFrame(credits_frame)
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Development Team
        dev_frame = ctk.CTkFrame(scroll_frame)
        dev_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            dev_frame,
            text="🔧 Development Team",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        ).pack(anchor="w", padx=15, pady=(10, 5))
        
        ctk.CTkLabel(
            dev_frame,
            text="Lead Developer - Sciandra Lorenzo\nGUI Design - CustomTkinter Framework\n3D Engine - Pyglet & OpenGL",
            font=ctk.CTkFont(size=12),
            text_color="#B0BEC5",
            justify="left",
            anchor="w"
        ).pack(anchor="w", padx=30, pady=(0, 10))
        
        # Libraries Used
        lib_frame = ctk.CTkFrame(scroll_frame)
        lib_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            lib_frame,
            text="📚 Libraries & Dependencies",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        ).pack(anchor="w", padx=15, pady=(10, 5))
        
        libs = [
            "• CustomTkinter - Modern UI framework",
            "• Pyglet - OpenGL window & graphics",
            "• Trimesh - 3D mesh processing",
            "• NumPy - Numerical computing",
            "• PIL/Pillow - Image processing"
        ]
        
        for lib in libs:
            ctk.CTkLabel(
                lib_frame,
                text=lib,
                font=ctk.CTkFont(size=12),
                text_color="#B0BEC5",
                anchor="w"
            ).pack(anchor="w", padx=30, pady=2)
        
        ctk.CTkLabel(lib_frame, text="").pack(pady=5)
        
        # Special Thanks
        thanks_frame = ctk.CTkFrame(scroll_frame)
        thanks_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            thanks_frame,
            text="💖 Special Thanks",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        ).pack(anchor="w", padx=15, pady=(10, 5))
        
        ctk.CTkLabel(
            thanks_frame,
            text="Thanks to the open-source community\nand all contributors who made this possible.",
            font=ctk.CTkFont(size=12),
            text_color="#B0BEC5",
            justify="left",
            anchor="w"
        ).pack(anchor="w", padx=30, pady=(0, 10))
        
        # Version Info
        version_frame = ctk.CTkFrame(scroll_frame)
        version_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            version_frame,
            text="ℹ️ Version Information",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        ).pack(anchor="w", padx=15, pady=(10, 5))
        
        ctk.CTkLabel(
            version_frame,
            text=f"Version: 1.5.0\nBuild Date: {datetime.now().strftime('%Y-%m-%d')}\nPython: {sys.version.split()[0]}",
            font=ctk.CTkFont(size=12),
            text_color="#B0BEC5",
            justify="left",
            anchor="w"
        ).pack(anchor="w", padx=30, pady=(0, 10))
        
        # Contact/Support
        contact_frame = ctk.CTkFrame(scroll_frame)
        contact_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            contact_frame,
            text="📧 Support & Contact",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        ).pack(anchor="w", padx=15, pady=(10, 5))
        
        ctk.CTkLabel(
            contact_frame,
            text="For support, bug reports, or feature requests:\nOpen an issue on GitHub or contact the development team.",
            font=ctk.CTkFont(size=12),
            text_color="#B0BEC5",
            justify="left",
            anchor="w"
        ).pack(anchor="w", padx=30, pady=(0, 10))
    
    # === METHODS ===
    
    def update_rotation_label(self, value):
        """Update rotation label"""
        self.rotation_label.configure(text=f"{int(float(value))}°")
    
    def browse_model(self):
        """Browse for model file"""
        filename = filedialog.askopenfilename(
            title="Select 3D Model",
            filetypes=[
                ("3D Models", "*.glb *.obj *.gltf"),
                ("GLB files (fastest)", "*.glb"),
                ("OBJ files", "*.obj"),
                ("GLTF files", "*.gltf"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.model_path.set(filename)
            self.viewer_terminal.log(f"Model selected: {Path(filename).name}", "#4CAF50")
    
    def browse_texture(self):
        """Browse for texture file"""
        filename = filedialog.askopenfilename(
            title="Select Texture",
            filetypes=[
                ("Images", "*.png *.jpg *.jpeg *.webp *.bmp *.tga"),
("PNG files", "*.png"),
                ("JPEG files", "*.jpg *.jpeg"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.texture_path.set(filename)
            self.viewer_terminal.log(f"Texture selected: {Path(filename).name}", "#4CAF50")
    
    def browse_convert_input(self):
        """Browse for OBJ to convert"""
        filename = filedialog.askopenfilename(
            title="Select OBJ File",
            filetypes=[("OBJ files", "*.obj"), ("All files", "*.*")]
        )
        if filename:
            self.conv_input.delete(0, "end")
            self.conv_input.insert(0, filename)
            
            # Auto-fill output
            output = str(Path(filename).with_suffix('.glb'))
            self.output_path.set(output)
            self.conv_output.delete(0, "end")
            self.conv_output.insert(0, output)
            
            self.viewer_terminal.log(f"Input OBJ: {Path(filename).name}", "#90CAF9")
    
    def browse_convert_output(self):
        """Browse for output GLB"""
        filename = filedialog.asksaveasfilename(
            title="Save GLB As",
            defaultextension=".glb",
            filetypes=[("GLB files", "*.glb"), ("All files", "*.*")]
        )
        if filename:
            self.output_path.set(filename)
            self.conv_output.delete(0, "end")
            self.conv_output.insert(0, filename)
    
    def launch_viewer(self):
        """Launch the 3D viewer with real-time output"""
        model = self.model_path.get()
        
        if not model:
            messagebox.showerror("Error", "Please select a 3D model file!")
            return
        
        if not Path(model).exists():
            messagebox.showerror("Error", f"File not found:\n{model}")
            return
        
        viewer_script = self.viewer_path_entry.get()
        
        # Check if script exists in current directory or is bundled
        if not Path(viewer_script).exists():
            # Try to find it in the same directory as the exe/script
            script_dir = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent
            alternative_path = script_dir / viewer_script
            
            if alternative_path.exists():
                viewer_script = str(alternative_path)
            else:
                messagebox.showerror(
                    "Error", 
                    f"Viewer script not found:\n{viewer_script}\n\n"
                    f"Also tried: {alternative_path}\n\n"
                    "Please check the path in Settings tab."
                )
                return
        
        # Build command with rotation parameter
        cmd = [sys.executable, viewer_script, model]
        
        texture = self.texture_path.get()
        if texture and Path(texture).exists():
            cmd.append(texture)
        
        # Add rotation offset if not zero
        rotation = self.rotation_offset.get()
        if rotation != 0:
            cmd.extend(["--rotation-offset", str(rotation)])
        
        try:
            self.viewer_terminal.log(f"═══════════════════════════════════════", "#4CAF50")
            self.viewer_terminal.log(f"Launching viewer: {Path(model).name}", "#4CAF50")
            self.viewer_terminal.log(f"Command: {' '.join(cmd)}", "#90CAF9")
            self.viewer_terminal.log(f"═══════════════════════════════════════", "#4CAF50")
            
            # Show viewer terminal
            self.viewer_terminal.deiconify()
            
            # Launch process and capture output
            self.viewer_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Start output monitoring thread
            threading.Thread(
                target=self._monitor_viewer_output,
                daemon=True
            ).start()
            
            # Add to recent
            self.add_to_recent(model)
            
            self.status_label.configure(text="✓ Viewer launched", text_color="#81C784")
            
        except Exception as e:
            self.viewer_terminal.log(f"Failed to launch: {str(e)}", "#EF5350")
            messagebox.showerror("Error", f"Failed to launch viewer:\n{str(e)}")
    
    def _monitor_viewer_output(self):
        """Monitor viewer process output in real-time"""
        if not self.viewer_process:
            return
        
        try:
            for line in iter(self.viewer_process.stdout.readline, ''):
                if line:
                    line = line.rstrip()
                    
                    # Color code based on content
                    color = "#E0E0E0"
                    if "error" in line.lower() or "failed" in line.lower():
                        color = "#EF5350"
                    elif "warning" in line.lower():
                        color = "#FF9800"
                    elif "success" in line.lower() or "loaded" in line.lower():
                        color = "#81C784"
                    
                    self.viewer_terminal.log(line, color)
            
            # Process finished
            returncode = self.viewer_process.wait()
            self.viewer_terminal.log(f"═══════════════════════════════════════", "#90CAF9")
            self.viewer_terminal.log(f"Viewer process finished (exit code: {returncode})", "#90CAF9")
            self.viewer_terminal.log(f"═══════════════════════════════════════", "#90CAF9")
            
        except Exception as e:
            self.viewer_terminal.log(f"Error monitoring output: {str(e)}", "#EF5350")
    
    def convert_obj_to_glb(self):
        """Convert OBJ to GLB in separate thread"""
        input_path = self.conv_input.get()
        output_path = self.conv_output.get()
        
        if not input_path:
            messagebox.showerror("Error", "Please select an input OBJ file!")
            return
        
        if not Path(input_path).exists():
            messagebox.showerror("Error", f"Input file not found:\n{input_path}")
            return
        
        if not output_path:
            messagebox.showerror("Error", "Please specify output GLB path!")
            return
        
        # Run in thread to not freeze GUI
        thread = threading.Thread(target=self._do_conversion, args=(input_path, output_path))
        thread.daemon = True
        thread.start()
    
    def _do_conversion(self, input_path, output_path):
        """Actual conversion (runs in thread)"""
        try:
            self.viewer_terminal.log(f"Converting: {Path(input_path).name}", "#90CAF9")
            self.progress_label.configure(text="Loading OBJ file...")
            self.progress_bar.set(0.2)
            
            # Load OBJ
            mesh = trimesh.load(input_path, process=False)
            
            self.progress_label.configure(text="Processing geometry...")
            self.progress_bar.set(0.5)
            
            # Handle scene
            if isinstance(mesh, trimesh.Scene):
                mesh = trimesh.util.concatenate(list(mesh.geometry.values()))
            
            self.progress_label.configure(text="Saving GLB...")
            self.progress_bar.set(0.8)
            
            # Export to GLB
            mesh.export(output_path, file_type='glb')
            
            self.progress_bar.set(1.0)
            
            # Get file sizes
            input_size = Path(input_path).stat().st_size / (1024**2)
            output_size = Path(output_path).stat().st_size / (1024**2)
            reduction = (1 - output_size/input_size) * 100
            
            message = f"✓ Conversion complete!\n\n"
            message += f"Input:  {input_size:.2f} MB (OBJ)\n"
            message += f"Output: {output_size:.2f} MB (GLB)\n"
            message += f"Size reduction: {reduction:.1f}%"
            
            self.progress_label.configure(text="✓ Conversion complete!")
            self.viewer_terminal.log(f"Conversion successful: {Path(output_path).name}", "#81C784")
            self.viewer_terminal.log(f"Size: {input_size:.2f}MB → {output_size:.2f}MB ({reduction:.1f}% reduction)", "#81C784")
            
            messagebox.showinfo("Success", message)
            
        except Exception as e:
            self.progress_bar.set(0)
            self.progress_label.configure(text="✗ Conversion failed")
            self.viewer_terminal.log(f"Conversion failed: {str(e)}", "#EF5350")
            messagebox.showerror("Error", f"Conversion failed:\n{str(e)}")
    
    def toggle_interactive_terminal(self):
        """Show/hide interactive terminal"""
        if self.interactive_terminal.winfo_viewable():
            self.interactive_terminal.withdraw()
        else:
            self.interactive_terminal.deiconify()
    
    def toggle_viewer_terminal(self):
        """Show/hide viewer terminal"""
        if self.viewer_terminal.winfo_viewable():
            self.viewer_terminal.withdraw()
        else:
            self.viewer_terminal.deiconify()
    
    def change_theme(self, theme):
        """Change application theme"""
        theme_map = {"Dark": "dark", "Light": "light", "System": "system"}
        ctk.set_appearance_mode(theme_map[theme])
        self.viewer_terminal.log(f"Theme changed to: {theme}", "#90CAF9")
    
    def add_to_recent(self, filepath):
        """Add file to recent list"""
        if filepath in self.recent_files:
            self.recent_files.remove(filepath)
        
        self.recent_files.insert(0, filepath)
        self.recent_files = self.recent_files[:10]
        
        self.save_config()
        self.update_recent_files()
    
    def update_layout_sizes(self):
        """Update sizes based on window dimensions"""
        if not self.winfo_viewable():
            return
        
        window_height = self.winfo_height()
        
        # Recent files scrollable area
        if hasattr(self, 'recent_scroll'):
            recent_height = max(150, min(400, int(window_height * 0.25)))
            self.recent_scroll.configure(height=recent_height)
    
    def update_recent_files(self):
        """Update recent files display"""
        # Clear existing
        for widget in self.recent_scroll.winfo_children():
            widget.destroy()
        
        if not self.recent_files:
            ctk.CTkLabel(
                self.recent_scroll,
                text="No recent files",
                text_color="#757575",
                font=ctk.CTkFont(size=12)
            ).pack(pady=20)
            return
        
        for filepath in self.recent_files:
            if not Path(filepath).exists():
                continue
            
            file_frame = ctk.CTkFrame(self.recent_scroll)
            file_frame.pack(fill="x", pady=3, padx=5)
            
            filename = Path(filepath).name
            file_size = Path(filepath).stat().st_size / (1024**2)
            
            # Info frame
            info_frame = ctk.CTkFrame(file_frame, fg_color="transparent")
            info_frame.pack(side="left", fill="x", expand=True)
            
            # Filename
            ctk.CTkLabel(
                info_frame,
                text=filename,
                font=ctk.CTkFont(size=13),
                anchor="w"
            ).pack(side="top", anchor="w", padx=10, pady=(8, 2))
            
            # Path and size
            path_text = f"{str(Path(filepath).parent)[:50]}... • {file_size:.1f} MB"
            ctk.CTkLabel(
                info_frame,
                text=path_text,
                font=ctk.CTkFont(size=10),
                text_color="#B0BEC5",
                anchor="w"
            ).pack(side="top", anchor="w", padx=10, pady=(0, 8))
            
            # Load button
            ctk.CTkButton(
                file_frame,
                text="Load",
                command=lambda p=filepath: self.load_recent(p),
                width=90,
                height=35
            ).pack(side="right", padx=8, pady=5)
    
    def load_recent(self, filepath):
        """Load from recent files"""
        self.model_path.set(filepath)
        self.viewer_terminal.log(f"Loaded recent file: {Path(filepath).name}", "#4CAF50")
    
    def load_config(self):
        """Load configuration"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.recent_files = [f for f in config.get('recent_files', []) 
                                        if Path(f).exists()]
            except:
                self.recent_files = []
    
    def save_config(self):
        """Save configuration"""
        config = {'recent_files': self.recent_files}
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except:
            pass
    
    def on_closing(self):
        """Handle window close"""
        # Kill viewer process if running
        if self.viewer_process and self.viewer_process.poll() is None:
            self.viewer_process.terminate()
        
        self.save_config()
        self.interactive_terminal.destroy()
        self.viewer_terminal.destroy()
        self.destroy()


if __name__ == '__main__':
    # Check dependencies
    try:
        import customtkinter
        import trimesh
    except ImportError as e:
        print(f"ERROR: Missing dependency: {e}")
        print("\nInstall with:")
        print("pip install customtkinter trimesh")
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    # Run GUI
    app = ViewerGUI()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()