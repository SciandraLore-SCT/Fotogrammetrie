"""
3D Model Viewer - Professional GUI
CustomTkinter version with OBJ to GLB converter
For non-programmers - Simple and intuitive
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

# Set appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class DebugConsole(ctk.CTkToplevel):
    """Debug console window"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Debug Console")
        self.geometry("800x500")
        
        # Text widget
        self.console = ctk.CTkTextbox(self, wrap="word", font=("Consolas", 11))
        self.console.pack(fill="both", expand=True, padx=10, pady=10)
        
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
        
        # Don't close on X, just hide
        self.protocol("WM_DELETE_WINDOW", self.hide_window)
        
    def log(self, message, level="INFO"):
        """Add message to console"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        colors = {
            "INFO": "#90CAF9",
            "SUCCESS": "#81C784",
            "WARNING": "#FFB74D",
            "ERROR": "#E57373"
        }
        
        self.console.insert("end", f"[{timestamp}] ", "timestamp")
        self.console.insert("end", f"{level}: ", level)
        self.console.insert("end", f"{message}\n")
        
        # Color tags
        self.console.tag_config("timestamp", foreground="#B0BEC5")
        self.console.tag_config(level, foreground=colors.get(level, "white"))
        
        # Auto-scroll
        self.console.see("end")
    
    def clear(self):
        """Clear console"""
        self.console.delete("1.0", "end")
    
    def copy_all(self):
        """Copy all text to clipboard"""
        text = self.console.get("1.0", "end")
        self.clipboard_clear()
        self.clipboard_append(text)
        self.log("Text copied to clipboard", "SUCCESS")
    
    def hide_window(self):
        """Hide instead of closing"""
        self.withdraw()


class ViewerGUI(ctk.CTk):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        # Window config
        self.title("3D Model Viewer Pro")
        self.geometry("900x700")
        self.resizable(False, False)
        
        # Variables
        self.model_path = ctk.StringVar()
        self.texture_path = ctk.StringVar()
        self.output_path = ctk.StringVar()
        
        # Config
        self.config_file = Path.home() / ".3d_viewer_config.json"
        self.recent_files = []
        
        # Debug console
        self.console = DebugConsole(self)
        self.console.withdraw()  # Hidden by default
        
        # Load config
        self.load_config()
        
        # Create UI
        self.create_ui()
        
        # Log startup
        self.log("Application started", "SUCCESS")
    
    def create_ui(self):
        """Create main interface"""
        
        # === HEADER ===
        header = ctk.CTkFrame(self, height=100, corner_radius=0)
        header.pack(fill="x", pady=(0, 20))
        
        title = ctk.CTkLabel(
            header,
            text="🎨 3D Model Viewer Pro",
            font=ctk.CTkFont(size=32, weight="bold")
        )
        title.pack(pady=(20, 5))
        
        subtitle = ctk.CTkLabel(
            header,
            text="Professional viewer for GLB, OBJ, GLTF with texture support",
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
        
        # === TAB 1: VIEWER ===
        self.create_viewer_tab(tab_viewer)
        
        # === TAB 2: CONVERTER ===
        self.create_converter_tab(tab_converter)
        
        # === TAB 3: SETTINGS ===
        self.create_settings_tab(tab_settings)
        
        # === FOOTER ===
        footer = ctk.CTkFrame(self, height=50, corner_radius=0)
        footer.pack(fill="x", side="bottom")
        
        # Debug button
        self.debug_btn = ctk.CTkButton(
            footer,
            text="📋 Debug Console",
            command=self.toggle_console,
            width=150,
            height=35
        )
        self.debug_btn.pack(side="left", padx=20, pady=10)
        
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
        
        # Format info
        format_label = ctk.CTkLabel(
            model_frame,
            text="💡 GLB format is 5-7x faster than OBJ!",
            font=ctk.CTkFont(size=11),
            text_color="#FFB74D"
        )
        format_label.pack(anchor="w", padx=10, pady=(0, 10))
        
        # Texture file section (optional)
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
        
        # Recent files
        recent_frame = ctk.CTkFrame(parent)
        recent_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        ctk.CTkLabel(
            recent_frame,
            text="Recent Files",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        # Scrollable frame for recent files
        self.recent_scroll = ctk.CTkScrollableFrame(recent_frame, height=150)
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
            placeholder_text="universal_viewer.py"
        )
        self.viewer_path_entry.pack(side="left", fill="x", expand=True, padx=(5, 5))
        self.viewer_path_entry.insert(0, "universal_viewer.py")
        
        # About
        about_frame = ctk.CTkFrame(parent)
        about_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        ctk.CTkLabel(
            about_frame,
            text="About",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        about_text = """
3D Model Viewer Pro v1.0

Features:
• Fast GLB/GLTF viewer (5-7x faster than OBJ)
• OBJ format support with texture loading
• Built-in OBJ to GLB converter
• Professional OpenGL rendering
• Interactive controls (rotate, zoom, pan)
• Opacity adjustment and wireframe mode

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
    
    # === METHODS ===
    
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
            self.log(f"Model selected: {Path(filename).name}", "INFO")
    
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
            self.log(f"Texture selected: {Path(filename).name}", "INFO")
    
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
            
            self.log(f"Input OBJ: {Path(filename).name}", "INFO")
    
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
        """Launch the 3D viewer"""
        model = self.model_path.get()
        
        if not model:
            messagebox.showerror("Error", "Please select a 3D model file!")
            return
        
        if not Path(model).exists():
            messagebox.showerror("Error", f"File not found:\n{model}")
            return
        
        viewer_script = self.viewer_path_entry.get()
        if not Path(viewer_script).exists():
            messagebox.showerror("Error", f"Viewer script not found:\n{viewer_script}")
            return
        
        # Build command
        cmd = [sys.executable, viewer_script, model]
        
        texture = self.texture_path.get()
        if texture and Path(texture).exists():
            cmd.append(texture)
        
        try:
            self.log(f"Launching viewer: {Path(model).name}", "INFO")
            subprocess.Popen(cmd)
            
            # Add to recent
            self.add_to_recent(model)
            
            self.status_label.configure(text="✓ Viewer launched", text_color="#81C784")
            self.log("Viewer launched successfully", "SUCCESS")
            
        except Exception as e:
            self.log(f"Failed to launch: {str(e)}", "ERROR")
            messagebox.showerror("Error", f"Failed to launch viewer:\n{str(e)}")
    
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
            self.log(f"Converting: {Path(input_path).name}", "INFO")
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
            self.log(f"Conversion successful: {Path(output_path).name}", "SUCCESS")
            self.log(f"Size: {input_size:.2f}MB → {output_size:.2f}MB ({reduction:.1f}% reduction)", "SUCCESS")
            
            messagebox.showinfo("Success", message)
            
        except Exception as e:
            self.progress_bar.set(0)
            self.progress_label.configure(text="✗ Conversion failed")
            self.log(f"Conversion failed: {str(e)}", "ERROR")
            messagebox.showerror("Error", f"Conversion failed:\n{str(e)}")
    
    def toggle_console(self):
        """Show/hide debug console"""
        if self.console.winfo_viewable():
            self.console.withdraw()
            self.debug_btn.configure(text="📋 Debug Console")
        else:
            self.console.deiconify()
            self.debug_btn.configure(text="📋 Hide Console")
    
    def change_theme(self, theme):
        """Change application theme"""
        theme_map = {"Dark": "dark", "Light": "light", "System": "system"}
        ctk.set_appearance_mode(theme_map[theme])
        self.log(f"Theme changed to: {theme}", "INFO")
    
    def add_to_recent(self, filepath):
        """Add file to recent list"""
        if filepath in self.recent_files:
            self.recent_files.remove(filepath)
        
        self.recent_files.insert(0, filepath)
        self.recent_files = self.recent_files[:10]
        
        self.save_config()
        self.update_recent_files()
    
    def update_recent_files(self):
        """Update recent files display"""
        # Clear existing
        for widget in self.recent_scroll.winfo_children():
            widget.destroy()
        
        if not self.recent_files:
            ctk.CTkLabel(
                self.recent_scroll,
                text="No recent files",
                text_color="#757575"
            ).pack(pady=20)
            return
        
        for filepath in self.recent_files:
            if not Path(filepath).exists():
                continue
            
            file_frame = ctk.CTkFrame(self.recent_scroll)
            file_frame.pack(fill="x", pady=2)
            
            filename = Path(filepath).name
            file_size = Path(filepath).stat().st_size / (1024**2)
            
            # Filename
            ctk.CTkLabel(
                file_frame,
                text=filename,
                font=ctk.CTkFont(size=12),
                anchor="w"
            ).pack(side="left", padx=10, pady=5)
            
            # Size
            ctk.CTkLabel(
                file_frame,
                text=f"{file_size:.1f} MB",
                font=ctk.CTkFont(size=10),
                text_color="#B0BEC5"
            ).pack(side="left", padx=5)
            
            # Load button
            ctk.CTkButton(
                file_frame,
                text="Load",
                command=lambda p=filepath: self.load_recent(p),
                width=80,
                height=28
            ).pack(side="right", padx=5)
    
    def load_recent(self, filepath):
        """Load from recent files"""
        self.model_path.set(filepath)
        self.log(f"Loaded recent file: {Path(filepath).name}", "INFO")
    
    def log(self, message, level="INFO"):
        """Log message to console"""
        self.console.log(message, level)
    
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
        self.save_config()
        self.console.destroy()
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