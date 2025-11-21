"""
OBJ 3D Viewer - Compatible with Pyglet 2.x
Multi-format texture support: PNG, JPEG, JPG, WEBP, BMP, TGA
Handles large OBJ files (2GB+)
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
            # Fallback to basic config if MSAA not supported
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
        self.rot_x = 20
        self.rot_y = 30
        self.distance = 5.0
        self.pan_x = 0
        self.pan_y = 0
        
        # Model
        self.vertex_list = None
        self.vertex_count = 0
        self.texture = None
        self.has_texture = False
        
        # State
        self.loaded = False
        self.error_msg = None
        self.loading_stage = "Initializing..."
        self.show_wireframe = False
        
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
        self.create_shader()
        
        # Load model
        pyglet.clock.schedule_once(self.load_model, 0.1)
    
    def setup_gl(self):
        """Setup OpenGL state"""
        pyglet.gl.glEnable(pyglet.gl.GL_DEPTH_TEST)
        pyglet.gl.glEnable(pyglet.gl.GL_CULL_FACE)
        pyglet.gl.glClearColor(0.1, 0.12, 0.15, 1.0)
    
    def create_shader(self):
        """Create simple shader program"""
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
            gl_Position = projection * view * model * vec4(position, 1.0);
            v_normal = normalize(mat3(model) * normal);
            v_color = color;
            v_texcoord = texcoord;
            v_pos = vec3(model * vec4(position, 1.0));
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
        
        void main() {
            // Simple lighting
            vec3 light_dir = normalize(light_pos - v_pos);
            vec3 view_dir = normalize(view_pos - v_pos);
            vec3 halfway = normalize(light_dir + view_dir);
            
            float ambient = 0.3;
            float diffuse = max(dot(v_normal, light_dir), 0.0) * 0.6;
            float specular = pow(max(dot(v_normal, halfway), 0.0), 32.0) * 0.3;
            
            float lighting = ambient + diffuse + specular;
            
            vec3 color;
            if (use_texture) {
                color = texture(tex, v_texcoord).rgb;
            } else {
                color = v_color;
            }
            
            fragColor = vec4(color * lighting, 1.0);
        }
        """
        
        self.shader = pyglet.graphics.shader.ShaderProgram(
            pyglet.graphics.shader.Shader(vertex_source, 'vertex'),
            pyglet.graphics.shader.Shader(fragment_source, 'fragment')
        )
    
    def load_texture(self, path):
        """Load texture"""
        if not path or not os.path.exists(path):
            return False
        
        try:
            print(f"\nLoading texture: {Path(path).name}")
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
            
            # Load texture
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
                maintain_order=True
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
            
            print(f"\nControls:")
            print(f"  Left drag:   Rotate")
            print(f"  Right drag:  Pan")
            print(f"  Scroll:      Zoom")
            print(f"  R:           Reset")
            print(f"  T:           Toggle texture")
            print(f"  W:           Wireframe")
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
        """Auto-find texture"""
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
        """Main render"""
        self.window.clear()
        
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
        
        # Use shader
        self.shader.use()
        self.shader['projection'] = projection
        self.shader['view'] = view
        self.shader['model'] = model
        self.shader['use_texture'] = self.has_texture and self.texture is not None
        self.shader['light_pos'] = (5.0, 5.0, 5.0)
        self.shader['view_pos'] = (self.pan_x, self.pan_y, self.distance)
        
        # Bind texture
        if self.has_texture and self.texture:
            pyglet.gl.glActiveTexture(pyglet.gl.GL_TEXTURE0)
            pyglet.gl.glBindTexture(pyglet.gl.GL_TEXTURE_2D, self.texture.id)
            self.shader['tex'] = 0
        
        # Wireframe
        if self.show_wireframe:
            pyglet.gl.glPolygonMode(pyglet.gl.GL_FRONT_AND_BACK, pyglet.gl.GL_LINE)
        else:
            pyglet.gl.glPolygonMode(pyglet.gl.GL_FRONT_AND_BACK, pyglet.gl.GL_FILL)
        
        # Draw
        self.vertex_list.draw(pyglet.gl.GL_TRIANGLES)
        
        # UI
        self.draw_ui()
    
    def draw_loading(self):
        """Loading screen"""
        title = pyglet.text.Label(
            'Loading OBJ Model',
            font_size=20,
            x=self.window.width // 2, y=self.window.height // 2 + 40,
            anchor_x='center', anchor_y='center'
        )
        title.draw()
        
        stage = pyglet.text.Label(
            self.loading_stage,
            font_size=14,
            x=self.window.width // 2, y=self.window.height // 2,
            anchor_x='center', anchor_y='center',
            color=(200, 200, 200, 255)
        )
        stage.draw()
        
        if self.file_size_mb > 0:
            info = pyglet.text.Label(
                f'File size: {self.file_size_mb:.1f} MB - Please wait...',
                font_size=11,
                x=self.window.width // 2, y=self.window.height // 2 - 40,
                anchor_x='center', anchor_y='center',
                color=(150, 150, 150, 255)
            )
            info.draw()
    
    def draw_error(self):
        """Error screen"""
        label = pyglet.text.Label(
            f'ERROR:\n\n{self.error_msg}',
            font_size=14,
            x=self.window.width // 2, y=self.window.height // 2,
            anchor_x='center', anchor_y='center',
            multiline=True, width=800,
            color=(255, 120, 120, 255)
        )
        label.draw()
    
    def draw_ui(self):
        """UI overlay"""
        stats = (
            f'Vertices: {self.vertex_count:,} | '
            f'Faces: {self.face_count:,} | '
            f'Zoom: {self.distance:.1f}x | '
            f'Texture: {"ON" if self.has_texture else "OFF"} | '
            f'Wireframe: {"ON" if self.show_wireframe else "OFF"}'
        )
        
        label = pyglet.text.Label(
            stats, font_size=11,
            x=10, y=self.window.height - 20,
            color=(220, 220, 220, 255)
        )
        label.draw()
    
    def on_drag(self, x, y, dx, dy, buttons, mods):
        """Mouse drag"""
        if buttons & mouse.LEFT:
            self.rot_y += dx * 0.5
            self.rot_x += dy * 0.5
        elif buttons & mouse.RIGHT:
            self.pan_x += dx * 0.01
            self.pan_y += dy * 0.01
    
    def on_scroll(self, x, y, sx, sy):
        """Mouse scroll"""
        self.distance -= sy * 0.3
        self.distance = max(1.0, min(50, self.distance))
    
    def on_key(self, symbol, mods):
        """Keyboard"""
        if symbol == key.ESCAPE:
            self.window.close()
        elif symbol == key.R:
            self.rot_x = 20
            self.rot_y = 30
            self.distance = 5.0
            self.pan_x = 0
            self.pan_y = 0
        elif symbol == key.T and self.texture:
            self.has_texture = not self.has_texture
        elif symbol == key.W:
            self.show_wireframe = not self.show_wireframe
    
    def on_resize(self, width, height):
        """Resize"""
        pyglet.gl.glViewport(0, 0, width, height)
    
    def run(self):
        """Start"""
        pyglet.app.run()


def main():
    print("\n" + "="*70)
    print("OBJ 3D Viewer")
    print("="*70)
    
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