"""
OBJ 3D Viewer - Complete Version
- Adjustable opacity in real-time
- Multi-format texture support
- Reference grid
- All pyglet 2.x compatible
"""

import sys
import os
from pathlib import Path

try:
    import pyglet
    from pyglet.window import key, mouse
    from pyglet import image
    from pyglet.graphics import Batch
    from pyglet.math import Mat4, Vec3
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
        # Create window with OpenGL 3.3+ context
        config = pyglet.gl.Config(
            major_version=3,
            minor_version=3,
            forward_compatible=True,
            double_buffer=True,
            depth_size=24,
            sample_buffers=1,
            samples=4
        )
        
        try:
            self.window = pyglet.window.Window(
                width=1400,
                height=900,
                caption='OBJ Viewer - Loading...',
                resizable=True,
                config=config
            )
        except:
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
        
        # Camera
        self.rot_x = 20.0
        self.rot_y = 30.0
        self.distance = 5.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        
        # Model
        self.vertex_list = None
        self.vertex_count = 0
        self.texture = None
        self.has_texture = False
        
        # Grid
        self.grid_vertex_list = None
        self.grid_shader = None
        
        # UI background shader
        self.ui_shader = None
        self.ui_bg_top = None
        self.ui_bg_bottom = None
        
        # State
        self.loaded = False
        self.error_msg = None
        self.loading_stage = "Initializing..."
        self.show_wireframe = False
        self.show_grid = True
        
        # Opacity control (adjustable in real-time)
        self.opacity = 1.0
        
        # Stats
        self.file_size_mb = 0
        self.face_count = 0
        
        # Shader program
        self.shader = None
        
        # Events
        self.window.on_draw = self.draw
        self.window.on_mouse_drag = self.on_drag
        self.window.on_mouse_scroll = self.on_scroll
        self.window.on_key_press = self.on_key
        self.window.on_resize = self.on_resize
        
        # Setup
        self.setup_gl()
        self.create_shaders()
        self.create_grid()
        self.create_ui_backgrounds()
        
        # Load model
        pyglet.clock.schedule_once(self.load_model, 0.1)
    
    def setup_gl(self):
        """Setup OpenGL state"""
        # Depth test for 3D
        pyglet.gl.glEnable(pyglet.gl.GL_DEPTH_TEST)
        pyglet.gl.glDepthFunc(pyglet.gl.GL_LESS)
        
        # Face culling
        pyglet.gl.glEnable(pyglet.gl.GL_CULL_FACE)
        pyglet.gl.glCullFace(pyglet.gl.GL_BACK)
        
        # Enable blending for opacity
        pyglet.gl.glEnable(pyglet.gl.GL_BLEND)
        pyglet.gl.glBlendFunc(pyglet.gl.GL_SRC_ALPHA, pyglet.gl.GL_ONE_MINUS_SRC_ALPHA)
        
        # Line width for wireframe and grid
        pyglet.gl.glLineWidth(1.5)
        
        pyglet.gl.glClearColor(0.1, 0.12, 0.15, 1.0)
    
    def create_shaders(self):
        """Create shader programs"""
        # Main model shader
        vertex_source = """
        #version 330 core
        
        in vec3 position;
        in vec3 normal;
        in vec3 color;
        in vec2 texcoord;
        
        out vec3 v_normal;
        out vec3 v_color;
        out vec2 v_texcoord;
        out vec3 v_pos;
        
        uniform mat4 projection;
        uniform mat4 view;
        uniform mat4 model;
        
        void main() {
            vec4 world_pos = model * vec4(position, 1.0);
            gl_Position = projection * view * world_pos;
            v_normal = normalize(mat3(model) * normal);
            v_color = color;
            v_texcoord = texcoord;
            v_pos = world_pos.xyz;
        }
        """
        
        fragment_source = """
        #version 330 core
        
        in vec3 v_normal;
        in vec3 v_color;
        in vec2 v_texcoord;
        in vec3 v_pos;
        
        out vec4 fragColor;
        
        uniform bool use_texture;
        uniform sampler2D tex;
        uniform vec3 light_pos;
        uniform vec3 view_pos;
        uniform float opacity;
        
        void main() {
            // Lighting calculation
            vec3 light_dir = normalize(light_pos - v_pos);
            vec3 view_dir = normalize(view_pos - v_pos);
            vec3 halfway = normalize(light_dir + view_dir);
            
            float ambient = 0.4;
            float diffuse = max(dot(v_normal, light_dir), 0.0) * 0.5;
            float specular = pow(max(dot(v_normal, halfway), 0.0), 32.0) * 0.2;
            
            float lighting = ambient + diffuse + specular;
            
            vec3 color;
            float alpha = opacity;
            
            if (use_texture) {
                vec4 tex_color = texture(tex, v_texcoord);
                color = tex_color.rgb;
                alpha *= tex_color.a;
            } else {
                color = v_color;
            }
            
            fragColor = vec4(color * lighting, alpha);
        }
        """
        
        self.shader = pyglet.graphics.shader.ShaderProgram(
            pyglet.graphics.shader.Shader(vertex_source, 'vertex'),
            pyglet.graphics.shader.Shader(fragment_source, 'fragment')
        )
        
        # Grid shader (simple, no lighting)
        grid_vertex_source = """
        #version 330 core
        
        in vec3 position;
        in vec3 color;
        
        out vec3 v_color;
        
        uniform mat4 projection;
        uniform mat4 view;
        uniform mat4 model;
        
        void main() {
            gl_Position = projection * view * model * vec4(position, 1.0);
            v_color = color;
        }
        """
        
        grid_fragment_source = """
        #version 330 core
        
        in vec3 v_color;
        out vec4 fragColor;
        
        void main() {
            fragColor = vec4(v_color, 1.0);
        }
        """
        
        self.grid_shader = pyglet.graphics.shader.ShaderProgram(
            pyglet.graphics.shader.Shader(grid_vertex_source, 'vertex'),
            pyglet.graphics.shader.Shader(grid_fragment_source, 'fragment')
        )
        
        # Simple 2D shader for UI backgrounds
        ui_vertex_source = """
        #version 330 core
        
        in vec2 position;
        
        uniform mat4 projection;
        
        void main() {
            gl_Position = projection * vec4(position, 0.0, 1.0);
        }
        """
        
        ui_fragment_source = """
        #version 330 core
        
        out vec4 fragColor;
        uniform vec4 color;
        
        void main() {
            fragColor = color;
        }
        """
        
        self.ui_shader = pyglet.graphics.shader.ShaderProgram(
            pyglet.graphics.shader.Shader(ui_vertex_source, 'vertex'),
            pyglet.graphics.shader.Shader(ui_fragment_source, 'fragment')
        )
    
    def create_grid(self):
        """Create reference grid"""
        grid_size = 10
        grid_spacing = 0.5
        
        vertices = []
        colors = []
        
        # Lines parallel to X axis
        for i in range(-grid_size, grid_size + 1):
            z = i * grid_spacing
            vertices.extend([
                -grid_size * grid_spacing, 0, z,
                grid_size * grid_spacing, 0, z
            ])
            # Center lines brighter
            if i == 0:
                colors.extend([0.5, 0.5, 0.5, 0.5, 0.5, 0.5])
            else:
                colors.extend([0.3, 0.3, 0.3, 0.3, 0.3, 0.3])
        
        # Lines parallel to Z axis
        for i in range(-grid_size, grid_size + 1):
            x = i * grid_spacing
            vertices.extend([
                x, 0, -grid_size * grid_spacing,
                x, 0, grid_size * grid_spacing
            ])
            if i == 0:
                colors.extend([0.5, 0.5, 0.5, 0.5, 0.5, 0.5])
            else:
                colors.extend([0.3, 0.3, 0.3, 0.3, 0.3, 0.3])
        
        vertex_count = len(vertices) // 3
        
        # Create vertex list with grid shader
        self.grid_vertex_list = self.grid_shader.vertex_list(
            vertex_count,
            pyglet.gl.GL_LINES,
            position=('f', vertices),
            color=('f', colors)
        )
    
    def create_ui_backgrounds(self):
        """Create UI background rectangles"""
        # Top bar (will be resized on window resize)
        self.update_ui_backgrounds()
    
    def update_ui_backgrounds(self):
        """Update UI background sizes based on window size"""
        # Top bar background
        top_vertices = [
            0, self.window.height - 60,
            self.window.width, self.window.height - 60,
            self.window.width, self.window.height,
            0, self.window.height,
            0, self.window.height - 60,
            self.window.width, self.window.height
        ]
        
        # Bottom bar background
        bottom_vertices = [
            0, 0,
            self.window.width, 0,
            self.window.width, 55,
            0, 55,
            0, 0,
            self.window.width, 55
        ]
        
        # Create vertex lists for backgrounds
        self.ui_bg_top = self.ui_shader.vertex_list(
            6,
            pyglet.gl.GL_TRIANGLES,
            position=('f', top_vertices)
        )
        
        self.ui_bg_bottom = self.ui_shader.vertex_list(
            6,
            pyglet.gl.GL_TRIANGLES,
            position=('f', bottom_vertices)
        )
    
    def load_texture(self, path):
        """Load texture from file"""
        if not path or not os.path.exists(path):
            return False
        
        try:
            ext = Path(path).suffix.lower()
            print(f"\nLoading texture: {Path(path).name} ({ext})")
            
            img = image.load(path)
            self.texture = img.get_texture()
            self.has_texture = True
            
            print(f"✓ Texture loaded: {img.width}x{img.height}px")
            return True
            
        except Exception as e:
            print(f"✗ Failed to load texture: {e}")
            return False
    
    def load_model(self, dt):
        """Load OBJ file"""
        try:
            self.file_size_mb = os.path.getsize(self.obj_path) / (1024**2)
            
            print(f"\n{'='*70}")
            print(f"Loading OBJ Model")
            print(f"{'='*70}")
            print(f"File: {Path(self.obj_path).name}")
            print(f"Size: {self.file_size_mb:.2f} MB")
            
            if self.file_size_mb > 100:
                print(f"⚠ Large file! This may take several minutes...")
            
            # Load texture first
            if self.texture_path:
                self.loading_stage = "Loading texture..."
                self.load_texture(self.texture_path)
            else:
                self.auto_find_texture()
            
            # Load OBJ
            self.loading_stage = "Loading OBJ geometry..."
            print(f"\nLoading OBJ file...")
            
            mesh = trimesh.load(
                self.obj_path,
                force='mesh',
                process=False,
                maintain_order=True,
                skip_materials=True
            )
            
            if isinstance(mesh, trimesh.Scene):
                print(f"Scene with {len(mesh.geometry)} meshes, merging...")
                mesh = trimesh.util.concatenate(list(mesh.geometry.values()))
            
            print(f"Vertices: {len(mesh.vertices):,}")
            print(f"Faces: {len(mesh.faces):,}")
            self.face_count = len(mesh.faces)
            
            # Process geometry
            self.loading_stage = "Processing geometry..."
            
            verts = mesh.vertices.astype(np.float32)
            center = verts.mean(axis=0)
            verts -= center
            max_extent = np.max(np.abs(verts))
            if max_extent > 0:
                verts *= 2.0 / max_extent
            
            # Prepare data
            vertices = verts[mesh.faces].reshape(-1, 3)
            
            # Normals
            if hasattr(mesh, 'vertex_normals'):
                normals = mesh.vertex_normals.astype(np.float32)[mesh.faces].reshape(-1, 3)
            else:
                mesh.fix_normals()
                normals = mesh.vertex_normals.astype(np.float32)[mesh.faces].reshape(-1, 3)
            
            # Colors
            if hasattr(mesh.visual, 'vertex_colors'):
                colors = (mesh.visual.vertex_colors[:, :3].astype(np.float32) / 255.0)[mesh.faces].reshape(-1, 3)
            else:
                colors = np.ones((len(vertices), 3), dtype=np.float32) * 0.75
            
            # UVs
            if hasattr(mesh.visual, 'uv') and mesh.visual.uv is not None:
                uvs = mesh.visual.uv.astype(np.float32)[mesh.faces].reshape(-1, 2)
                print(f"✓ UV mapping found")
            else:
                uvs = np.zeros((len(vertices), 2), dtype=np.float32)
                print("⚠ No UV mapping")
            
            self.vertex_count = len(vertices)
            
            # Create vertex list
            self.vertex_list = self.shader.vertex_list(
                self.vertex_count,
                pyglet.gl.GL_TRIANGLES,
                position=('f', vertices.flatten().tolist()),
                normal=('f', normals.flatten().tolist()),
                color=('f', colors.flatten().tolist()),
                texcoord=('f', uvs.flatten().tolist())
            )
            
            self.loaded = True
            
            print(f"\n{'='*70}")
            print(f"✓ Model loaded successfully!")
            print(f"{'='*70}")
            print(f"Vertices: {self.vertex_count:,}")
            print(f"Texture: {'Yes' if self.has_texture else 'No'}")
            
            self.window.set_caption(f'OBJ Viewer - {Path(self.obj_path).name}')
            
            print(f"\n{'Controls:'}")
            print(f"  Left drag:       Rotate model")
            print(f"  Right drag:      Pan camera")
            print(f"  Scroll:          Zoom in/out")
            print(f"  +/- (or =/_ ):   Increase/Decrease opacity")
            print(f"  1:               10% opacity")
            print(f"  5:               50% opacity")
            print(f"  0:               100% opacity (fully opaque)")
            print(f"  R:               Reset view")
            print(f"  T:               Toggle texture")
            print(f"  W:               Toggle wireframe")
            print(f"  G:               Toggle grid")
            print(f"  F:               Fullscreen")
            print(f"  ESC:             Exit")
            
        except Exception as e:
            self.error_msg = str(e)
            print(f"\n{'='*70}")
            print(f"✗ ERROR: {e}")
            print(f"{'='*70}")
            import traceback
            traceback.print_exc()
            self.window.set_caption('Error loading model')
    
    def auto_find_texture(self):
        """Auto-find texture file"""
        obj_dir = Path(self.obj_path).parent
        obj_name = Path(self.obj_path).stem
        
        patterns = [f"{obj_name}.*", "texture.*", "diffuse.*"]
        formats = ['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tga']
        
        for pattern in patterns:
            for tex_file in obj_dir.glob(pattern):
                if tex_file.suffix.lower() in formats and tex_file != Path(self.obj_path):
                    if self.load_texture(str(tex_file)):
                        return True
        return False
    
    def draw(self):
        """Main render function"""
        # Clear buffers
        pyglet.gl.glClear(pyglet.gl.GL_COLOR_BUFFER_BIT | pyglet.gl.GL_DEPTH_BUFFER_BIT)
        
        if self.error_msg:
            self.draw_error()
            return
        
        if not self.loaded:
            self.draw_loading()
            return
        
        # Projection matrix
        aspect = self.window.width / self.window.height
        projection = Mat4.perspective_projection(aspect, 45, 0.1, 100.0)
        
        # View matrix
        view = Mat4()
        view = view.translate(Vec3(self.pan_x, self.pan_y, -self.distance))
        view = view.rotate(self.rot_x * 0.01745329, Vec3(1, 0, 0))
        view = view.rotate(self.rot_y * 0.01745329, Vec3(0, 1, 0))
        
        # Model matrix
        model = Mat4()
        
        # Draw grid first (behind everything)
        if self.show_grid:
            self.draw_grid(projection, view, model)
        
        # Draw model
        self.shader.use()
        self.shader['projection'] = projection
        self.shader['view'] = view
        self.shader['model'] = model
        self.shader['use_texture'] = self.has_texture and self.texture is not None
        self.shader['light_pos'] = (5.0, 5.0, 5.0)
        self.shader['view_pos'] = (self.pan_x, self.pan_y, self.distance)
        self.shader['opacity'] = self.opacity
        
        # CRITICAL: Disable culling when transparency is used
        if self.opacity < 1.0:
            pyglet.gl.glDisable(pyglet.gl.GL_CULL_FACE)
            pyglet.gl.glDepthMask(pyglet.gl.GL_FALSE)
        else:
            pyglet.gl.glEnable(pyglet.gl.GL_CULL_FACE)
            pyglet.gl.glDepthMask(pyglet.gl.GL_TRUE)
        
        # Bind texture
        if self.has_texture and self.texture:
            pyglet.gl.glActiveTexture(pyglet.gl.GL_TEXTURE0)
            pyglet.gl.glBindTexture(pyglet.gl.GL_TEXTURE_2D, self.texture.id)
            self.shader['tex'] = 0
        
        # Wireframe mode
        if self.show_wireframe:
            pyglet.gl.glPolygonMode(pyglet.gl.GL_FRONT_AND_BACK, pyglet.gl.GL_LINE)
        else:
            pyglet.gl.glPolygonMode(pyglet.gl.GL_FRONT_AND_BACK, pyglet.gl.GL_FILL)
        
        # Draw model
        self.vertex_list.draw(pyglet.gl.GL_TRIANGLES)
        
        # Reset states
        pyglet.gl.glPolygonMode(pyglet.gl.GL_FRONT_AND_BACK, pyglet.gl.GL_FILL)
        pyglet.gl.glEnable(pyglet.gl.GL_CULL_FACE)
        pyglet.gl.glDepthMask(pyglet.gl.GL_TRUE)
        
        # Draw UI overlay
        self.draw_ui()
    
    def draw_grid(self, projection, view, model):
        """Draw reference grid"""
        # Draw grid behind everything
        pyglet.gl.glDepthMask(pyglet.gl.GL_FALSE)
        
        self.grid_shader.use()
        self.grid_shader['projection'] = projection
        self.grid_shader['view'] = view
        self.grid_shader['model'] = model
        
        self.grid_vertex_list.draw(pyglet.gl.GL_LINES)
        
        # Re-enable depth writes
        pyglet.gl.glDepthMask(pyglet.gl.GL_TRUE)
    
    def draw_loading(self):
        """Loading screen with proper text rendering"""
        # Disable depth test for 2D UI
        pyglet.gl.glDisable(pyglet.gl.GL_DEPTH_TEST)
        
        # Create labels individually (not batched) for better rendering
        title = pyglet.text.Label(
            'Loading OBJ Model',
            font_name='Consolas',  # Monospace font più leggibile
            font_size=26,
            x=self.window.width // 2, 
            y=self.window.height // 2 + 80,
            anchor_x='center', 
            anchor_y='center',
            color=(255, 255, 255, 255)
        )
        title.draw()
        
        stage = pyglet.text.Label(
            self.loading_stage,
            font_name='Consolas',
            font_size=18,
            x=self.window.width // 2, 
            y=self.window.height // 2,
            anchor_x='center', 
            anchor_y='center',
            color=(220, 220, 220, 255)
        )
        stage.draw()
        
        if self.file_size_mb > 0:
            info = pyglet.text.Label(
                f'File size: {self.file_size_mb:.1f} MB - Please wait...',
                font_name='Consolas',
                font_size=14,
                x=self.window.width // 2, 
                y=self.window.height // 2 - 80,
                anchor_x='center', 
                anchor_y='center',
                color=(180, 180, 180, 255)
            )
            info.draw()
        
        # Re-enable depth test
        pyglet.gl.glEnable(pyglet.gl.GL_DEPTH_TEST)
    
    def draw_error(self):
        """Error screen with proper text rendering"""
        pyglet.gl.glDisable(pyglet.gl.GL_DEPTH_TEST)
        
        label = pyglet.text.Label(
            f'ERROR:\n\n{self.error_msg}',
            font_name='Consolas',
            font_size=18,
            x=self.window.width // 2, 
            y=self.window.height // 2,
            anchor_x='center', 
            anchor_y='center',
            multiline=True, 
            width=900,
            color=(255, 150, 150, 255)
        )
        label.draw()
        
        pyglet.gl.glEnable(pyglet.gl.GL_DEPTH_TEST)
    
    def draw_ui(self):
        """UI overlay with clear, readable text"""
        # Disable depth test for UI rendering
        pyglet.gl.glDisable(pyglet.gl.GL_DEPTH_TEST)
        
        # Create 2D orthographic projection for UI
        projection_2d = Mat4.orthogonal_projection(0, self.window.width, 0, self.window.height, -1, 1)
        
        # Draw background bars using shader
        self.ui_shader.use()
        self.ui_shader['projection'] = projection_2d
        self.ui_shader['color'] = (0.0, 0.0, 0.0, 0.75)  # Semi-transparent black
        
        # Draw top background
        self.ui_bg_top.draw(pyglet.gl.GL_TRIANGLES)
        
        # Draw bottom background
        self.ui_bg_bottom.draw(pyglet.gl.GL_TRIANGLES)
        
        # Now draw text on top of backgrounds
        # Stats bar at top
        stats_text = (
            f'Vertices: {self.vertex_count:,} | '
            f'Faces: {self.face_count:,} | '
            f'Zoom: {self.distance:.1f}x | '
            f'Opacity: {int(self.opacity * 100)}% | '
            f'Texture: {"ON" if self.has_texture else "OFF"} | '
            f'Wireframe: {"ON" if self.show_wireframe else "OFF"} | '
            f'Grid: {"ON" if self.show_grid else "OFF"}'
        )
        
        label_stats = pyglet.text.Label(
            stats_text,
            font_name='Consolas',
            font_size=14,
            x=25,
            y=self.window.height - 35,
            anchor_x='left',
            anchor_y='center',
            color=(240, 240, 240, 255)
        )
        label_stats.draw()
        
        # Controls bar at bottom
        controls_text = (
            'LMB: Rotate | RMB: Pan | Scroll: Zoom | +/-: Opacity | '
            '1-9: Opacity 10-90% | 0: 100% | R: Reset | T: Texture | W: Wire | G: Grid | F: Full'
        )
        
        label_controls = pyglet.text.Label(
            controls_text,
            font_name='Consolas',
            font_size=12,
            x=25,
            y=27,
            anchor_x='left',
            anchor_y='center',
            color=(220, 220, 220, 255)
        )
        label_controls.draw()
        
        # Re-enable depth test
        pyglet.gl.glEnable(pyglet.gl.GL_DEPTH_TEST)
    
    def on_drag(self, x, y, dx, dy, buttons, mods):
        """Mouse drag handler"""
        if buttons & mouse.LEFT:
            self.rot_y += dx * 0.5
            self.rot_x += dy * 0.5
        elif buttons & mouse.RIGHT:
            self.pan_x += dx * 0.01 * (self.distance / 5)
            self.pan_y += dy * 0.01 * (self.distance / 5)
    
    def on_scroll(self, x, y, sx, sy):
        """Mouse scroll handler"""
        self.distance -= sy * 0.3
        self.distance = max(1.0, min(50, self.distance))
    
    def on_key(self, symbol, mods):
        """Keyboard handler"""
        if symbol == key.ESCAPE:
            self.window.close()
        
        elif symbol == key.R:
            self.rot_x = 20.0
            self.rot_y = 30.0
            self.distance = 5.0
            self.pan_x = 0.0
            self.pan_y = 0.0
            print("View reset")
        
        elif symbol == key.F:
            self.window.set_fullscreen(not self.window.fullscreen)
            print(f"Fullscreen: {'ON' if self.window.fullscreen else 'OFF'}")
        
        elif symbol == key.T and self.texture:
            self.has_texture = not self.has_texture
            print(f"Texture: {'ON' if self.has_texture else 'OFF'}")
        
        elif symbol == key.W:
            self.show_wireframe = not self.show_wireframe
            print(f"Wireframe: {'ON' if self.show_wireframe else 'OFF'}")
        
        elif symbol == key.G:
            self.show_grid = not self.show_grid
            print(f"Grid: {'ON' if self.show_grid else 'OFF'}")
        
        # Opacity controls
        elif symbol == key.PLUS or symbol == key.EQUAL:
            self.opacity = min(1.0, self.opacity + 0.1)
            print(f"Opacity: {self.opacity:.1f}")
        
        elif symbol == key.MINUS or symbol == key.UNDERSCORE:
            self.opacity = max(0.1, self.opacity - 0.1)
            print(f"Opacity: {self.opacity:.1f}")
        
        elif symbol == key._1:
            self.opacity = 0.1
            print(f"Opacity: 10%")
        
        elif symbol == key._2:
            self.opacity = 0.2
            print(f"Opacity: 20%")
        
        elif symbol == key._3:
            self.opacity = 0.3
            print(f"Opacity: 30%")
        
        elif symbol == key._4:
            self.opacity = 0.4
            print(f"Opacity: 40%")
        
        elif symbol == key._5:
            self.opacity = 0.5
            print(f"Opacity: 50%")
        
        elif symbol == key._6:
            self.opacity = 0.6
            print(f"Opacity: 60%")
        
        elif symbol == key._7:
            self.opacity = 0.7
            print(f"Opacity: 70%")
        
        elif symbol == key._8:
            self.opacity = 0.8
            print(f"Opacity: 80%")
        
        elif symbol == key._9:
            self.opacity = 0.9
            print(f"Opacity: 90%")
        
        elif symbol == key._0:
            self.opacity = 1.0
            print(f"Opacity: 100% (fully opaque)")
    
    def on_resize(self, width, height):
        """Window resize handler"""
        pyglet.gl.glViewport(0, 0, width, height)
        # Update UI backgrounds for new window size
        self.update_ui_backgrounds()
    
    def run(self):
        """Start the viewer"""
        pyglet.app.run()


def main():
    """Entry point"""
    print("\n" + "="*70)
    print("OBJ 3D Viewer - Complete Edition")
    print("="*70)
    print("Features: Adjustable opacity, Reference grid, Multi-format textures")
    print("="*70 + "\n")
    
    obj_path = None
    texture_path = None
    
    if len(sys.argv) >= 2:
        obj_path = sys.argv[1]
        if len(sys.argv) >= 3:
            texture_path = sys.argv[2]
    else:
        obj_files = list(Path('.').glob('*.obj'))
        if obj_files:
            obj_path = str(obj_files[0])
            print(f"Found: {obj_path}")
        else:
            print("ERROR: No OBJ file found!")
            print(f"\nUsage: python {sys.argv[0]} <model.obj> [texture.png]")
            input("\nPress Enter to exit...")
            return
    
    if not os.path.exists(obj_path):
        print(f"\nERROR: File not found: {obj_path}")
        input("\nPress Enter to exit...")
        return
    
    if texture_path and not os.path.exists(texture_path):
        print(f"\nWARNING: Texture not found: {texture_path}")
        texture_path = None
    
    file_size_mb = os.path.getsize(obj_path) / (1024**2)
    if file_size_mb > 500:
        print(f"\n⚠ WARNING: Very large file ({file_size_mb:.0f} MB)")
        print("Loading may take several minutes")
        print("Ensure you have enough free memory (recommended: 8GB+ free)\n")
    
    viewer = OBJViewer(obj_path, texture_path)
    viewer.run()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted")
    except Exception as e:
        print(f"\n\n{'='*70}")
        print("FATAL ERROR")
        print("="*70)
        print(f"{e}\n")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")