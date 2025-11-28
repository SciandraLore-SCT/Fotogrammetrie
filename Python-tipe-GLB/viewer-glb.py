"""
Universal 3D Model Viewer
Supports: OBJ and GLB/GLTF formats
Features: Adjustable opacity, Reference grid, External textures
Optimized for large files (2GB+)
"""

import sys
import os
import time
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


class UniversalViewer:
    def __init__(self, model_path, texture_path=None):
        # Create window
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
                caption='3D Viewer - Loading...',
                resizable=True,
                config=config
            )
        except:
            config = pyglet.gl.Config(double_buffer=True, depth_size=24)
            self.window = pyglet.window.Window(
                width=1400,
                height=900,
                caption='3D Viewer - Loading...',
                resizable=True,
                config=config
            )
        
        self.model_path = model_path
        self.texture_path = texture_path
        self.model_format = Path(model_path).suffix.lower()
        
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
        
        # UI
        self.ui_shader = None
        self.ui_bg_top = None
        self.ui_bg_bottom = None
        
        # State
        self.loaded = False
        self.error_msg = None
        self.loading_stage = "Initializing..."
        self.show_wireframe = False
        self.show_grid = True
        self.opacity = 1.0
        
        # Stats
        self.file_size_mb = 0
        self.face_count = 0
        
        # Shader
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
        pyglet.gl.glEnable(pyglet.gl.GL_DEPTH_TEST)
        pyglet.gl.glDepthFunc(pyglet.gl.GL_LESS)
        pyglet.gl.glEnable(pyglet.gl.GL_CULL_FACE)
        pyglet.gl.glCullFace(pyglet.gl.GL_BACK)
        pyglet.gl.glEnable(pyglet.gl.GL_BLEND)
        pyglet.gl.glBlendFunc(pyglet.gl.GL_SRC_ALPHA, pyglet.gl.GL_ONE_MINUS_SRC_ALPHA)
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
        
        # Grid shader
        grid_vs = """
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
        
        grid_fs = """
        #version 330 core
        in vec3 v_color;
        out vec4 fragColor;
        void main() {
            fragColor = vec4(v_color, 1.0);
        }
        """
        
        self.grid_shader = pyglet.graphics.shader.ShaderProgram(
            pyglet.graphics.shader.Shader(grid_vs, 'vertex'),
            pyglet.graphics.shader.Shader(grid_fs, 'fragment')
        )
        
        # UI shader
        ui_vs = """
        #version 330 core
        in vec2 position;
        uniform mat4 projection;
        void main() {
            gl_Position = projection * vec4(position, 0.0, 1.0);
        }
        """
        
        ui_fs = """
        #version 330 core
        out vec4 fragColor;
        uniform vec4 color;
        void main() {
            fragColor = color;
        }
        """
        
        self.ui_shader = pyglet.graphics.shader.ShaderProgram(
            pyglet.graphics.shader.Shader(ui_vs, 'vertex'),
            pyglet.graphics.shader.Shader(ui_fs, 'fragment')
        )
    
    def create_grid(self):
        """Create reference grid"""
        grid_size = 10
        grid_spacing = 0.5
        vertices = []
        colors = []
        
        for i in range(-grid_size, grid_size + 1):
            z = i * grid_spacing
            vertices.extend([-grid_size * grid_spacing, 0, z, grid_size * grid_spacing, 0, z])
            col = [0.5, 0.5, 0.5] if i == 0 else [0.3, 0.3, 0.3]
            colors.extend(col * 2)
        
        for i in range(-grid_size, grid_size + 1):
            x = i * grid_spacing
            vertices.extend([x, 0, -grid_size * grid_spacing, x, 0, grid_size * grid_spacing])
            col = [0.5, 0.5, 0.5] if i == 0 else [0.3, 0.3, 0.3]
            colors.extend(col * 2)
        
        self.grid_vertex_list = self.grid_shader.vertex_list(
            len(vertices) // 3,
            pyglet.gl.GL_LINES,
            position=('f', vertices),
            color=('f', colors)
        )
    
    def create_ui_backgrounds(self):
        """Create UI background rectangles"""
        self.update_ui_backgrounds()
    
    def update_ui_backgrounds(self):
        """Update UI backgrounds for window size"""
        top_verts = [
            0, self.window.height - 60, self.window.width, self.window.height - 60,
            self.window.width, self.window.height, 0, self.window.height - 60,
            self.window.width, self.window.height, 0, self.window.height
        ]
        
        bottom_verts = [
            0, 0, self.window.width, 0, self.window.width, 55,
            0, 0, self.window.width, 55, 0, 55
        ]
        
        self.ui_bg_top = self.ui_shader.vertex_list(6, pyglet.gl.GL_TRIANGLES, position=('f', top_verts))
        self.ui_bg_bottom = self.ui_shader.vertex_list(6, pyglet.gl.GL_TRIANGLES, position=('f', bottom_verts))
    
    def load_texture(self, path):
        """Load texture"""
        if not path or not os.path.exists(path):
            return False
        try:
            print(f"\nLoading texture: {Path(path).name}")
            img = image.load(path)
            self.texture = img.get_texture()
            self.has_texture = True
            print(f"✓ Texture: {img.width}x{img.height}px")
            return True
        except Exception as e:
            print(f"✗ Texture failed: {e}")
            return False
    
    def auto_find_texture(self):
        """Auto-find texture"""
        model_dir = Path(self.model_path).parent
        model_name = Path(self.model_path).stem
        formats = ['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tga']
        
        for pattern in [f"{model_name}.*", "texture.*", "diffuse.*"]:
            for tex in model_dir.glob(pattern):
                if tex.suffix.lower() in formats and tex != Path(self.model_path):
                    if self.load_texture(str(tex)):
                        return True
        return False
    
    def load_model(self, dt):
        """Load model (OBJ or GLB)"""
        try:
            self.file_size_mb = os.path.getsize(self.model_path) / (1024**2)
            
            print(f"\n{'='*70}")
            print(f"Loading 3D Model ({self.model_format.upper()})")
            print(f"{'='*70}")
            print(f"File: {Path(self.model_path).name}")
            print(f"Size: {self.file_size_mb:.2f} MB")
            
            # Load texture
            if self.texture_path:
                self.loading_stage = "Loading texture..."
                self.load_texture(self.texture_path)
            else:
                self.auto_find_texture()
            
            # Load model
            self.loading_stage = f"Loading {self.model_format.upper()} file..."
            print(f"\nLoading {self.model_format.upper()} (optimized)...")
            
            start_time = time.time()
            
            # GLB is MUCH faster than OBJ (binary format)
            if self.model_format in ['.glb', '.gltf']:
                print("Using fast GLB loader...")
                mesh = trimesh.load(
                    self.model_path,
                    force='mesh',
                    process=False
                )
            else:
                # OBJ format
                print("Using OBJ loader...")
                mesh = trimesh.load(
                    self.model_path,
                    force='mesh',
                    process=False,
                    skip_materials=True,
                    validate=False
                )
            
            load_time = time.time() - start_time
            print(f"✓ Loaded in {load_time:.2f}s")
            
            # Handle scene
            if isinstance(mesh, trimesh.Scene):
                print(f"Scene with {len(mesh.geometry)} objects, merging...")
                mesh = trimesh.util.concatenate(list(mesh.geometry.values()))
            
            print(f"Vertices: {len(mesh.vertices):,}")
            print(f"Faces: {len(mesh.faces):,}")
            self.face_count = len(mesh.faces)
            
            # Process geometry
            start_proc = time.time()
            verts = mesh.vertices.astype(np.float32, copy=False)
            
            # Center and scale
            center = verts.mean(axis=0)
            verts = verts - center
            max_extent = np.max(np.abs(verts))
            if max_extent > 0:
                verts *= (2.0 / max_extent)
            
            faces = mesh.faces
            
            # Normals
            if hasattr(mesh, 'vertex_normals') and mesh.vertex_normals is not None:
                normals = mesh.vertex_normals.astype(np.float32, copy=False)
            else:
                print("Computing normals...")
                normals = np.zeros_like(verts)
                for face in faces:
                    v0, v1, v2 = verts[face[0]], verts[face[1]], verts[face[2]]
                    fn = np.cross(v1 - v0, v2 - v0)
                    normals[face[0]] += fn
                    normals[face[1]] += fn
                    normals[face[2]] += fn
                norms = np.linalg.norm(normals, axis=1, keepdims=True)
                norms[norms == 0] = 1
                normals = normals / norms
            
            # Colors
            if hasattr(mesh.visual, 'vertex_colors') and mesh.visual.vertex_colors is not None:
                colors = (mesh.visual.vertex_colors[:, :3].astype(np.float32, copy=False) / 255.0)
            else:
                colors = np.full((len(verts), 3), 0.75, dtype=np.float32)
            
            # UVs
            if hasattr(mesh.visual, 'uv') and mesh.visual.uv is not None:
                uvs = mesh.visual.uv.astype(np.float32, copy=False)
                print("✓ UV mapping")
            else:
                uvs = np.zeros((len(verts), 2), dtype=np.float32)
                print("⚠ No UVs")
            
            print(f"Processed in {time.time() - start_proc:.2f}s")
            
            # Upload to GPU
            start_gpu = time.time()
            
            self.vertex_list = self.shader.vertex_list_indexed(
                len(verts),
                pyglet.gl.GL_TRIANGLES,
                faces.flatten().tolist(),
                position=('f', verts.flatten().tolist()),
                normal=('f', normals.flatten().tolist()),
                color=('f', colors.flatten().tolist()),
                texcoord=('f', uvs.flatten().tolist())
            )
            
            self.vertex_count = len(verts)
            print(f"GPU upload: {time.time() - start_gpu:.2f}s")
            
            total = time.time() - start_time
            
            self.loaded = True
            print(f"\n{'='*70}")
            print(f"✓ SUCCESS!")
            print(f"{'='*70}")
            print(f"Total: {total:.2f}s | Speed: {self.file_size_mb/total:.1f} MB/s")
            print(f"Vertices: {self.vertex_count:,} | Faces: {self.face_count:,}")
            
            self.window.set_caption(f'3D Viewer - {Path(self.model_path).name}')
            
            print(f"\nControls:")
            print(f"  Drag Left:   Rotate | Drag Right: Pan | Scroll: Zoom")
            print(f"  +/-:         Opacity | 1-9: 10-90% | 0: 100%")
            print(f"  R: Reset | T: Texture | W: Wire | G: Grid | F: Full | ESC: Exit")
            
        except Exception as e:
            self.error_msg = str(e)
            print(f"\n{'='*70}\n✗ ERROR: {e}\n{'='*70}")
            import traceback
            traceback.print_exc()
    
    def draw(self):
        """Main render"""
        pyglet.gl.glClear(pyglet.gl.GL_COLOR_BUFFER_BIT | pyglet.gl.GL_DEPTH_BUFFER_BIT)
        
        if self.error_msg:
            self.draw_error()
            return
        
        if not self.loaded:
            self.draw_loading()
            return
        
        aspect = self.window.width / self.window.height
        projection = Mat4.perspective_projection(aspect, 45, 0.1, 100.0)
        view = Mat4()
        view = view.translate(Vec3(self.pan_x, self.pan_y, -self.distance))
        view = view.rotate(self.rot_x * 0.01745329, Vec3(1, 0, 0))
        view = view.rotate(self.rot_y * 0.01745329, Vec3(0, 1, 0))
        model = Mat4()
        
        if self.show_grid:
            self.draw_grid(projection, view, model)
        
        self.shader.use()
        self.shader['projection'] = projection
        self.shader['view'] = view
        self.shader['model'] = model
        self.shader['use_texture'] = self.has_texture and self.texture is not None
        self.shader['light_pos'] = (5.0, 5.0, 5.0)
        self.shader['view_pos'] = (self.pan_x, self.pan_y, self.distance)
        self.shader['opacity'] = self.opacity
        
        if self.opacity < 1.0:
            pyglet.gl.glDisable(pyglet.gl.GL_CULL_FACE)
            pyglet.gl.glDepthMask(pyglet.gl.GL_FALSE)
        else:
            pyglet.gl.glEnable(pyglet.gl.GL_CULL_FACE)
            pyglet.gl.glDepthMask(pyglet.gl.GL_TRUE)
        
        if self.has_texture and self.texture:
            pyglet.gl.glActiveTexture(pyglet.gl.GL_TEXTURE0)
            pyglet.gl.glBindTexture(pyglet.gl.GL_TEXTURE_2D, self.texture.id)
            self.shader['tex'] = 0
        
        if self.show_wireframe:
            pyglet.gl.glPolygonMode(pyglet.gl.GL_FRONT_AND_BACK, pyglet.gl.GL_LINE)
        
        self.vertex_list.draw(pyglet.gl.GL_TRIANGLES)
        
        pyglet.gl.glPolygonMode(pyglet.gl.GL_FRONT_AND_BACK, pyglet.gl.GL_FILL)
        pyglet.gl.glEnable(pyglet.gl.GL_CULL_FACE)
        pyglet.gl.glDepthMask(pyglet.gl.GL_TRUE)
        
        self.draw_ui()
    
    def draw_grid(self, projection, view, model):
        """Draw grid"""
        pyglet.gl.glDepthMask(pyglet.gl.GL_FALSE)
        self.grid_shader.use()
        self.grid_shader['projection'] = projection
        self.grid_shader['view'] = view
        self.grid_shader['model'] = model
        self.grid_vertex_list.draw(pyglet.gl.GL_LINES)
        pyglet.gl.glDepthMask(pyglet.gl.GL_TRUE)
    
    def draw_loading(self):
        """Loading screen"""
        pyglet.gl.glDisable(pyglet.gl.GL_DEPTH_TEST)
        
        pyglet.text.Label('Loading 3D Model', font_name='Consolas', font_size=26,
            x=self.window.width//2, y=self.window.height//2+80,
            anchor_x='center', anchor_y='center', color=(255,255,255,255)).draw()
        
        pyglet.text.Label(self.loading_stage, font_name='Consolas', font_size=18,
            x=self.window.width//2, y=self.window.height//2,
            anchor_x='center', anchor_y='center', color=(220,220,220,255)).draw()
        
        if self.file_size_mb > 0:
            pyglet.text.Label(f'Size: {self.file_size_mb:.1f} MB', font_name='Consolas', font_size=14,
                x=self.window.width//2, y=self.window.height//2-80,
                anchor_x='center', anchor_y='center', color=(180,180,180,255)).draw()
        
        pyglet.gl.glEnable(pyglet.gl.GL_DEPTH_TEST)
    
    def draw_error(self):
        """Error screen"""
        pyglet.gl.glDisable(pyglet.gl.GL_DEPTH_TEST)
        pyglet.text.Label(f'ERROR:\n\n{self.error_msg}', font_name='Consolas', font_size=18,
            x=self.window.width//2, y=self.window.height//2,
            anchor_x='center', anchor_y='center', multiline=True, width=900,
            color=(255,150,150,255)).draw()
        pyglet.gl.glEnable(pyglet.gl.GL_DEPTH_TEST)
    
    def draw_ui(self):
        """UI overlay"""
        pyglet.gl.glDisable(pyglet.gl.GL_DEPTH_TEST)
        
        projection_2d = Mat4.orthogonal_projection(0, self.window.width, 0, self.window.height, -1, 1)
        self.ui_shader.use()
        self.ui_shader['projection'] = projection_2d
        self.ui_shader['color'] = (0.0, 0.0, 0.0, 0.75)
        self.ui_bg_top.draw(pyglet.gl.GL_TRIANGLES)
        self.ui_bg_bottom.draw(pyglet.gl.GL_TRIANGLES)
        
        stats = (f'Vertices: {self.vertex_count:,} | Faces: {self.face_count:,} | '
                 f'Zoom: {self.distance:.1f}x | Opacity: {int(self.opacity*100)}% | '
                 f'Texture: {"ON" if self.has_texture else "OFF"} | '
                 f'Wire: {"ON" if self.show_wireframe else "OFF"} | Grid: {"ON" if self.show_grid else "OFF"}')
        
        pyglet.text.Label(stats, font_name='Consolas', font_size=14,
            x=25, y=self.window.height-35, anchor_x='left', anchor_y='center',
            color=(240,240,240,255)).draw()
        
        controls = 'LMB: Rotate | RMB: Pan | Scroll: Zoom | +/-: Opacity | 1-9/0: Presets | R: Reset | T/W/G/F'
        pyglet.text.Label(controls, font_name='Consolas', font_size=12,
            x=25, y=27, anchor_x='left', anchor_y='center',
            color=(220,220,220,255)).draw()
        
        pyglet.gl.glEnable(pyglet.gl.GL_DEPTH_TEST)
    
    def on_drag(self, x, y, dx, dy, buttons, mods):
        if buttons & mouse.LEFT:
            self.rot_y += dx * 0.5
            self.rot_x += dy * 0.5
        elif buttons & mouse.RIGHT:
            self.pan_x += dx * 0.01 * (self.distance / 5)
            self.pan_y += dy * 0.01 * (self.distance / 5)
    
    def on_scroll(self, x, y, sx, sy):
        self.distance -= sy * 0.3
        self.distance = max(1.0, min(50, self.distance))
    
    def on_key(self, symbol, mods):
        if symbol == key.ESCAPE:
            self.window.close()
        elif symbol == key.R:
            self.rot_x = self.rot_y = 20.0
            self.distance = 5.0
            self.pan_x = self.pan_y = 0.0
        elif symbol == key.F:
            self.window.set_fullscreen(not self.window.fullscreen)
        elif symbol == key.T and self.texture:
            self.has_texture = not self.has_texture
        elif symbol == key.W:
            self.show_wireframe = not self.show_wireframe
        elif symbol == key.G:
            self.show_grid = not self.show_grid
        elif symbol == key.PLUS or symbol == key.EQUAL:
            self.opacity = min(1.0, self.opacity + 0.1)
        elif symbol == key.MINUS or symbol == key.UNDERSCORE:
            self.opacity = max(0.1, self.opacity - 0.1)
        elif symbol in [key._1, key._2, key._3, key._4, key._5, key._6, key._7, key._8, key._9]:
            self.opacity = int(chr(symbol)) / 10.0
        elif symbol == key._0:
            self.opacity = 1.0
    
    def on_resize(self, width, height):
        pyglet.gl.glViewport(0, 0, width, height)
        self.update_ui_backgrounds()
    
    def run(self):
        pyglet.app.run()


def main():
    print("\n" + "="*70)
    print("Universal 3D Viewer - OBJ & GLB Support")
    print("="*70)
    
    model_path = None
    texture_path = None
    
    if len(sys.argv) >= 2:
        model_path = sys.argv[1]
        if len(sys.argv) >= 3:
            texture_path = sys.argv[2]
    else:
        # Auto-find model
        for ext in ['*.obj', '*.glb', '*.gltf']:
            files = list(Path('.').glob(ext))
            if files:
                model_path = str(files[0])
                print(f"Found: {model_path}")
                break
        
        if not model_path:
            print("ERROR: No model found!")
            print(f"Usage: python {sys.argv[0]} <model.obj|glb> [texture.png]")
            input("\nPress Enter to exit...")
            return
    
    if not os.path.exists(model_path):
        print(f"ERROR: File not found: {model_path}")
        input("\nPress Enter to exit...")
        return
    
    if texture_path and not os.path.exists(texture_path):
        print(f"WARNING: Texture not found: {texture_path}")
        texture_path = None
    
    viewer = UniversalViewer(model_path, texture_path)
    viewer.run()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted")
    except Exception as e:
        print(f"\n{'='*70}\nFATAL ERROR\n{'='*70}\n{e}\n")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")
        