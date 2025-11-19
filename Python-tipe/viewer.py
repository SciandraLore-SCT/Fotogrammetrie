"""
OBJ 3D Viewer with Multi-Format Texture Support
Supports: PNG, JPEG, JPG, WEBP, BMP, TGA
Handles large OBJ files (2GB+)
Fixed for pyglet 2.x OpenGL compatibility
"""

import sys
import os
from pathlib import Path

# Import pyglet and OpenGL
try:
    import pyglet
    from pyglet.window import key, mouse
    from pyglet import image
    import pyglet.gl as pgl
    from pyglet.gl import gl
except ImportError:
    print("ERROR: pyglet not installed!")
    print("Install with: pip install pyglet")
    input("Press Enter to exit...")
    sys.exit(1)

try:
    import trimesh
    import numpy as np
except ImportError:
    print("ERROR: trimesh not installed!")
    print("Install with: pip install trimesh")
    input("Press Enter to exit...")
    sys.exit(1)


class OBJViewer:
    def __init__(self, obj_path, texture_path=None):
        # Create window
        config = pyglet.gl.Config(double_buffer=True, depth_size=24)
        self.window = pyglet.window.Window(
            width=1400,
            height=900,
            caption='OBJ Viewer - Loading...',
            resizable=True,
            config=config
        )
        
        self.obj_path = obj_path
        self.texture_path = texture_path
        
        # Camera controls
        self.rot_x = 20
        self.rot_y = 30
        self.zoom = 5.0
        self.pan_x = 0
        self.pan_y = 0
        
        # Model data
        self.vertices = None
        self.normals = None
        self.uvs = None
        self.colors = None
        self.vertex_count = 0
        
        # Texture
        self.texture = None
        self.has_texture = False
        
        # State
        self.loaded = False
        self.error_msg = None
        self.loading_stage = "Initializing..."
        
        # Rendering options
        self.show_wireframe = False
        
        # Stats
        self.file_size_mb = 0
        self.face_count = 0
        
        # Setup OpenGL
        self.setup_gl()
        
        # Register events
        self.window.on_draw = self.draw
        self.window.on_mouse_drag = self.on_drag
        self.window.on_mouse_scroll = self.on_scroll
        self.window.on_key_press = self.on_key
        self.window.on_resize = self.on_resize
        
        # Schedule loading
        pyglet.clock.schedule_once(self.load_model, 0.1)
    
    def setup_gl(self):
        """Initialize OpenGL settings"""
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glDepthFunc(gl.GL_LEQUAL)
        gl.glEnable(gl.GL_CULL_FACE)
        gl.glCullFace(gl.GL_BACK)
        gl.glFrontFace(gl.GL_CCW)
        
        # Lighting
        gl.glEnable(gl.GL_LIGHTING)
        gl.glEnable(gl.GL_LIGHT0)
        gl.glEnable(gl.GL_LIGHT1)
        
        # Main light
        gl.glLightfv(gl.GL_LIGHT0, gl.GL_POSITION, (gl.GLfloat * 4)(10, 10, 10, 1))
        gl.glLightfv(gl.GL_LIGHT0, gl.GL_AMBIENT, (gl.GLfloat * 4)(0.3, 0.3, 0.3, 1))
        gl.glLightfv(gl.GL_LIGHT0, gl.GL_DIFFUSE, (gl.GLfloat * 4)(0.8, 0.8, 0.8, 1))
        gl.glLightfv(gl.GL_LIGHT0, gl.GL_SPECULAR, (gl.GLfloat * 4)(0.5, 0.5, 0.5, 1))
        
        # Fill light
        gl.glLightfv(gl.GL_LIGHT1, gl.GL_POSITION, (gl.GLfloat * 4)(-10, 5, -10, 1))
        gl.glLightfv(gl.GL_LIGHT1, gl.GL_DIFFUSE, (gl.GLfloat * 4)(0.4, 0.4, 0.4, 1))
        
        gl.glEnable(gl.GL_COLOR_MATERIAL)
        gl.glColorMaterial(gl.GL_FRONT_AND_BACK, gl.GL_AMBIENT_AND_DIFFUSE)
        
        # Material properties
        gl.glMaterialfv(gl.GL_FRONT_AND_BACK, gl.GL_SPECULAR, (gl.GLfloat * 4)(0.3, 0.3, 0.3, 1))
        gl.glMaterialf(gl.GL_FRONT_AND_BACK, gl.GL_SHININESS, 20)
        
        gl.glClearColor(0.1, 0.12, 0.15, 1)
        
        # Smooth shading
        gl.glShadeModel(gl.GL_SMOOTH)
        gl.glHint(gl.GL_PERSPECTIVE_CORRECTION_HINT, gl.GL_NICEST)
    
    def load_texture(self, path):
        """Load texture from various formats"""
        if not path or not os.path.exists(path):
            return False
        
        try:
            ext = Path(path).suffix.lower()
            print(f"\nLoading texture: {Path(path).name} ({ext})")
            
            # Load image
            img = image.load(path)
            
            # Get texture
            self.texture = img.get_texture()
            
            # Enable texture mapping
            gl.glEnable(gl.GL_TEXTURE_2D)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR_MIPMAP_LINEAR)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_REPEAT)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_REPEAT)
            
            print(f"✓ Texture loaded: {img.width}x{img.height}px")
            self.has_texture = True
            return True
            
        except Exception as e:
            print(f"✗ Failed to load texture: {e}")
            return False
    
    def load_model(self, dt):
        """Load OBJ file and texture"""
        try:
            # Get file info
            self.file_size_mb = os.path.getsize(self.obj_path) / (1024**2)
            
            print(f"\n{'='*70}")
            print(f"Loading OBJ Model")
            print(f"{'='*70}")
            print(f"File: {Path(self.obj_path).name}")
            print(f"Size: {self.file_size_mb:.2f} MB")
            
            if self.file_size_mb > 100:
                print(f"⚠ Large file! This may take several minutes...")
            
            # Stage 1: Load texture first (faster)
            if self.texture_path:
                self.loading_stage = "Loading texture..."
                self.load_texture(self.texture_path)
            else:
                # Try to auto-find texture
                self.auto_find_texture()
            
            # Stage 2: Load OBJ
            self.loading_stage = "Loading OBJ geometry..."
            print(f"\nLoading OBJ file...")
            
            mesh = trimesh.load(
                self.obj_path,
                force='mesh',
                process=False,
                maintain_order=True
            )
            
            # Handle scene with multiple meshes
            if isinstance(mesh, trimesh.Scene):
                print(f"Scene detected with {len(mesh.geometry)} objects")
                self.loading_stage = "Merging meshes..."
                meshes = list(mesh.geometry.values())
                if len(meshes) > 0:
                    mesh = trimesh.util.concatenate(meshes)
            
            self.loading_stage = "Processing geometry..."
            
            print(f"Vertices: {len(mesh.vertices):,}")
            print(f"Faces: {len(mesh.faces):,}")
            self.face_count = len(mesh.faces)
            
            # Get vertices
            verts = mesh.vertices.astype(np.float32)
            
            # Center and normalize
            self.loading_stage = "Centering model..."
            center = verts.mean(axis=0)
            verts -= center
            max_extent = np.max(np.abs(verts))
            if max_extent > 0:
                scale = 2.0 / max_extent
                verts *= scale
            
            # Prepare data for rendering
            self.loading_stage = "Preparing GPU data..."
            
            # Vertices
            self.vertices = verts[mesh.faces].flatten()
            self.vertex_count = len(self.vertices) // 3
            
            # Normals
            if hasattr(mesh, 'vertex_normals') and mesh.vertex_normals is not None:
                self.normals = mesh.vertex_normals.astype(np.float32)[mesh.faces].flatten()
            else:
                print("Computing normals...")
                mesh.fix_normals()
                self.normals = mesh.vertex_normals.astype(np.float32)[mesh.faces].flatten()
            
            # UV coordinates
            if hasattr(mesh.visual, 'uv') and mesh.visual.uv is not None:
                uvs = mesh.visual.uv.astype(np.float32)
                self.uvs = uvs[mesh.faces].flatten()
                print(f"✓ UV mapping found")
            else:
                print("⚠ No UV mapping in OBJ")
                self.uvs = None
            
            # Vertex colors as fallback
            if hasattr(mesh.visual, 'vertex_colors') and mesh.visual.vertex_colors is not None:
                cols = mesh.visual.vertex_colors[:, :3].astype(np.float32) / 255.0
                self.colors = cols[mesh.faces].flatten()
            else:
                # Default gray color
                self.colors = np.ones(self.vertex_count * 3, dtype=np.float32) * 0.75
            
            self.loaded = True
            self.loading_stage = "Ready!"
            
            print(f"\n{'='*70}")
            print(f"✓ Model loaded successfully!")
            print(f"{'='*70}")
            print(f"GPU Vertices: {self.vertex_count:,}")
            print(f"Texture: {'Yes' if self.has_texture else 'No'}")
            print(f"UV Mapping: {'Yes' if self.uvs is not None else 'No'}")
            
            self.window.set_caption(f'OBJ Viewer - {Path(self.obj_path).name}')
            
            print(f"\n{'Controls:':<15}")
            print(f"  Left drag:   Rotate model")
            print(f"  Right drag:  Pan camera")
            print(f"  Scroll:      Zoom in/out")
            print(f"  R:           Reset view")
            print(f"  T:           Toggle texture")
            print(f"  W:           Toggle wireframe")
            print(f"  F:           Fullscreen")
            print(f"  ESC:         Exit")
            
        except Exception as e:
            self.error_msg = str(e)
            print(f"\n{'='*70}")
            print(f"✗ ERROR: {e}")
            print(f"{'='*70}")
            import traceback
            traceback.print_exc()
            self.window.set_caption('Error loading model')
    
    def auto_find_texture(self):
        """Try to find texture file automatically"""
        obj_dir = Path(self.obj_path).parent
        obj_name = Path(self.obj_path).stem
        
        # Common texture naming patterns
        patterns = [
            f"{obj_name}.*",
            f"{obj_name}_texture.*",
            f"{obj_name}_diffuse.*",
            "texture.*",
            "diffuse.*",
        ]
        
        # Supported formats
        formats = ['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tga']
        
        for pattern in patterns:
            for tex_file in obj_dir.glob(pattern):
                if tex_file.suffix.lower() in formats and tex_file != Path(self.obj_path):
                    print(f"Auto-found texture: {tex_file.name}")
                    if self.load_texture(str(tex_file)):
                        self.texture_path = str(tex_file)
                        return True
        
        return False
    
    def draw(self):
        """Main render function"""
        self.window.clear()
        
        if self.error_msg:
            self.draw_error()
            return
        
        if not self.loaded:
            self.draw_loading()
            return
        
        # Setup 3D projection
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        aspect = self.window.width / self.window.height
        gl.gluPerspective(45, aspect, 0.1, 100)
        
        # Setup camera
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()
        gl.glTranslatef(self.pan_x, self.pan_y, -self.zoom)
        gl.glRotatef(self.rot_x, 1, 0, 0)
        gl.glRotatef(self.rot_y, 0, 1, 0)
        
        # Draw model
        self.draw_model()
        
        # Draw UI overlay
        self.draw_ui()
    
    def draw_model(self):
        """Render the 3D model"""
        # Wireframe mode
        if self.show_wireframe:
            gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_LINE)
        else:
            gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_FILL)
        
        # Bind texture if available
        if self.has_texture and self.texture and self.uvs is not None:
            gl.glEnable(gl.GL_TEXTURE_2D)
            gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture.id)
        else:
            gl.glDisable(gl.GL_TEXTURE_2D)
        
        # Enable vertex arrays
        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
        gl.glEnableClientState(gl.GL_NORMAL_ARRAY)
        gl.glEnableClientState(gl.GL_COLOR_ARRAY)
        
        gl.glVertexPointer(3, gl.GL_FLOAT, 0, self.vertices.ctypes.data)
        gl.glNormalPointer(gl.GL_FLOAT, 0, self.normals.ctypes.data)
        gl.glColorPointer(3, gl.GL_FLOAT, 0, self.colors.ctypes.data)
        
        # Enable UV if available
        if self.uvs is not None and self.has_texture:
            gl.glEnableClientState(gl.GL_TEXTURE_COORD_ARRAY)
            gl.glTexCoordPointer(2, gl.GL_FLOAT, 0, self.uvs.ctypes.data)
        
        # Draw
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, self.vertex_count)
        
        # Cleanup
        gl.glDisableClientState(gl.GL_VERTEX_ARRAY)
        gl.glDisableClientState(gl.GL_NORMAL_ARRAY)
        gl.glDisableClientState(gl.GL_COLOR_ARRAY)
        if self.uvs is not None:
            gl.glDisableClientState(gl.GL_TEXTURE_COORD_ARRAY)
    
    def draw_loading(self):
        """Loading screen"""
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        gl.glOrtho(0, self.window.width, 0, self.window.height, -1, 1)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()
        
        title = pyglet.text.Label(
            'Loading OBJ Model',
            font_size=20,
            bold=True,
            x=self.window.width // 2,
            y=self.window.height // 2 + 40,
            anchor_x='center',
            anchor_y='center'
        )
        title.draw()
        
        stage = pyglet.text.Label(
            self.loading_stage,
            font_size=14,
            x=self.window.width // 2,
            y=self.window.height // 2,
            anchor_x='center',
            anchor_y='center',
            color=(200, 200, 200, 255)
        )
        stage.draw()
        
        if self.file_size_mb > 0:
            info = pyglet.text.Label(
                f'File size: {self.file_size_mb:.1f} MB - Please wait...',
                font_size=11,
                x=self.window.width // 2,
                y=self.window.height // 2 - 40,
                anchor_x='center',
                anchor_y='center',
                color=(150, 150, 150, 255)
            )
            info.draw()
    
    def draw_error(self):
        """Error screen"""
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        gl.glOrtho(0, self.window.width, 0, self.window.height, -1, 1)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()
        
        label = pyglet.text.Label(
            f'ERROR LOADING MODEL:\n\n{self.error_msg}',
            font_size=14,
            x=self.window.width // 2,
            y=self.window.height // 2,
            anchor_x='center',
            anchor_y='center',
            multiline=True,
            width=800,
            color=(255, 120, 120, 255)
        )
        label.draw()
    
    def draw_ui(self):
        """Draw UI overlay"""
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        gl.glOrtho(0, self.window.width, 0, self.window.height, -1, 1)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()
        
        stats = (
            f'Vertices: {self.vertex_count:,} | '
            f'Faces: {self.face_count:,} | '
            f'Zoom: {self.zoom:.1f}x | '
            f'Texture: {"ON" if self.has_texture else "OFF"} | '
            f'Wireframe: {"ON" if self.show_wireframe else "OFF"}'
        )
        
        label_stats = pyglet.text.Label(
            stats,
            font_size=11,
            x=10,
            y=self.window.height - 20,
            color=(220, 220, 220, 255)
        )
        label_stats.draw()
        
        controls = 'LMB: Rotate | RMB: Pan | Scroll: Zoom | R: Reset | T: Texture | W: Wireframe'
        label_controls = pyglet.text.Label(
            controls,
            font_size=10,
            x=10,
            y=10,
            color=(170, 170, 170, 255)
        )
        label_controls.draw()
    
    def on_drag(self, x, y, dx, dy, buttons, mods):
        """Mouse drag handler"""
        if buttons & mouse.LEFT:
            self.rot_y += dx * 0.5
            self.rot_x += dy * 0.5
        elif buttons & mouse.RIGHT:
            self.pan_x += dx * 0.01 * (self.zoom / 5)
            self.pan_y += dy * 0.01 * (self.zoom / 5)
    
    def on_scroll(self, x, y, sx, sy):
        """Mouse scroll handler"""
        self.zoom -= sy * 0.3
        self.zoom = max(1.0, min(50, self.zoom))
    
    def on_key(self, symbol, mods):
        """Keyboard handler"""
        if symbol == key.ESCAPE:
            self.window.close()
        
        elif symbol == key.R:
            self.rot_x = 20
            self.rot_y = 30
            self.zoom = 5.0
            self.pan_x = 0
            self.pan_y = 0
            print("View reset")
        
        elif symbol == key.F:
            self.window.set_fullscreen(not self.window.fullscreen)
        
        elif symbol == key.T and self.texture:
            self.has_texture = not self.has_texture
            print(f"Texture: {'ON' if self.has_texture else 'OFF'}")
        
        elif symbol == key.W:
            self.show_wireframe = not self.show_wireframe
            print(f"Wireframe: {'ON' if self.show_wireframe else 'OFF'}")
    
    def on_resize(self, width, height):
        """Window resize handler"""
        gl.glViewport(0, 0, width, height)
    
    def run(self):
        """Start the viewer"""
        pyglet.app.run()


def main():
    """Entry point"""
    print("\n" + "="*70)
    print("OBJ 3D Viewer - Multi-Format Texture Support")
    print("="*70)
    print("Supported textures: PNG, JPEG, JPG, WEBP, BMP, TGA")
    print("="*70 + "\n")
    
    obj_path = None
    texture_path = None
    
    if len(sys.argv) >= 2:
        obj_path = sys.argv[1]
        if len(sys.argv) >= 3:
            texture_path = sys.argv[2]
    else:
        print("No arguments provided, searching for OBJ file...\n")
        obj_files = list(Path('.').glob('*.obj'))
        
        if obj_files:
            obj_path = str(obj_files[0])
            print(f"Found: {obj_path}")
            
            texture_formats = ['*.png', '*.jpg', '*.jpeg', '*.webp', '*.bmp', '*.tga']
            for pattern in texture_formats:
                tex_files = list(Path('.').glob(pattern))
                if tex_files:
                    texture_path = str(tex_files[0])
                    print(f"Found texture: {texture_path}")
                    break
        else:
            print("ERROR: No OBJ file found!")
            print("\nUsage:")
            print(f"  python {sys.argv[0]} <model.obj> [texture.png]")
            print("\nOr drag and drop files onto the executable")
            input("\nPress Enter to exit...")
            return
    
    if not os.path.exists(obj_path):
        print(f"\nERROR: OBJ file not found: {obj_path}")
        input("\nPress Enter to exit...")
        return
    
    if texture_path and not os.path.exists(texture_path):
        print(f"\nWARNING: Texture file not found: {texture_path}")
        print("Will try to auto-detect texture...\n")
        texture_path = None
    
    file_size_mb = os.path.getsize(obj_path) / (1024**2)
    if file_size_mb > 500:
        print(f"\n⚠ WARNING: Very large file ({file_size_mb:.0f} MB)")
        print("Loading may take several minutes and use significant RAM")
        print("Ensure you have enough free memory (recommended: 8GB+ free)\n")
    
    viewer = OBJViewer(obj_path, texture_path)
    viewer.run()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n\n{'='*70}")
        print("FATAL ERROR")
        print("="*70)
        print(f"{e}\n")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")