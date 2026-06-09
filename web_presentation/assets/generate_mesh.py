from PIL import Image
import numpy as np
import scipy.ndimage as ndimage

def generate_obj(input_path, output_path, scale_x=1755, scale_z=940, height=20):
    print(f"Processing {input_path}...")
    
    # 1. Load and Clean Mask
    img = Image.open(input_path).convert("RGB")
    data = np.array(img).astype(float)
    
    brightness = np.mean(data, axis=2)
    mask = brightness > 110
    
    labeled_array, num_features = ndimage.label(mask)
    sizes = ndimage.sum(mask, labeled_array, range(num_features + 1))
    mask_size = sizes < 2000
    remove_pixel = mask_size[labeled_array]
    mask[remove_pixel] = False
    mask = ndimage.binary_fill_holes(mask)
    
    # 2. Downsample
    GRID_W = 400
    ratio = GRID_W / mask.shape[1]
    GRID_H = int(mask.shape[0] * ratio)
    
    mask_img = Image.fromarray(mask.astype('uint8') * 255)
    mask_small = mask_img.resize((GRID_W, GRID_H), resample=Image.NEAREST)
    mask_grid = np.array(mask_small) > 128
    
    print(f"Grid Size: {GRID_W}x{GRID_H}")
    
    vertices = []
    uvs = [] # Texture Coordinates
    faces = []
    
    cell_w = scale_x / GRID_W
    cell_d = scale_z / GRID_H
    
    off_x = -scale_x / 2
    off_z = -scale_z / 2
    
    # Helper to add vertex + UV
    def add_vert(x, y, z, u, v):
        vertices.append((x, y, z))
        uvs.append((u, v))
        return len(vertices)
    
    for r in range(GRID_H):
        for c in range(GRID_W):
            if mask_grid[r, c]:
                # World Coords
                x1 = off_x + c * cell_w
                z1 = off_z + r * cell_d
                x2 = x1 + cell_w
                z2 = z1 + cell_d
                
                # UV Coords (0 to 1)
                # Image Y is inverted relative to 3D Z usually, but let's match grid
                u1 = c / GRID_W
                v1 = 1.0 - (r / GRID_H) # Flip V
                u2 = (c + 1) / GRID_W
                v2 = 1.0 - ((r + 1) / GRID_H)
                
                h = height
                
                # TOP FACE (Asphalt)
                # Top needs accurate UVs to look like the map
                vt1 = add_vert(x1, h, z1, u1, v1)
                vt2 = add_vert(x1, h, z2, u1, v2)
                vt3 = add_vert(x2, h, z2, u2, v2)
                vt4 = add_vert(x2, h, z1, u2, v1)
                
                faces.append((vt1, vt2, vt3, vt4))
                
                # WALLS (We can stretch the edge texture or just use a generic concrete color)
                # For now, let's just reuse the edge UVs so it has *some* texture, 
                # even if stretched vertically.
                
                # North Wall
                if r == 0 or not mask_grid[r-1, c]:
                    wb1 = add_vert(x2, 0, z1, u2, v1) # Bottom
                    wb2 = add_vert(x1, 0, z1, u1, v1)
                    faces.append((vt4, vt1, wb2, wb1))
                    
                # South Wall
                if r == GRID_H-1 or not mask_grid[r+1, c]:
                    wb1 = add_vert(x1, 0, z2, u1, v2)
                    wb2 = add_vert(x2, 0, z2, u2, v2)
                    faces.append((vt2, vt3, wb2, wb1))
                    
                # West Wall
                if c == 0 or not mask_grid[r, c-1]:
                    wb1 = add_vert(x1, 0, z1, u1, v1)
                    wb2 = add_vert(x1, 0, z2, u1, v2)
                    faces.append((vt1, vt2, wb2, wb1))

                # East Wall
                if c == GRID_W-1 or not mask_grid[r, c+1]:
                    wb1 = add_vert(x2, 0, z2, u2, v2)
                    wb2 = add_vert(x2, 0, z1, u2, v1)
                    faces.append((vt3, vt4, wb2, wb1))

    # 4. Write OBJ with UVs
    with open(output_path, "w") as f:
        f.write("# Textured Port Mesh\n")
        
        # Vertices
        for v in vertices:
            f.write(f"v {v[0]:.2f} {v[1]:.2f} {v[2]:.2f}\n")
            
        # UVs
        for uv in uvs:
            f.write(f"vt {uv[0]:.4f} {uv[1]:.4f}\n")
            
        # Normals (Up)
        f.write("vn 0.0 1.0 0.0\n")
        
        # Faces
        for face in faces:
            # f v1/vt1/vn1 v2/vt2/vn2 ...
            f.write(f"f {face[0]}/{face[0]}/1 {face[1]}/{face[1]}/1 {face[2]}/{face[2]}/1 {face[3]}/{face[3]}/1\n")
            
    print(f"Saved {len(vertices)} vertices to {output_path}")

if __name__ == "__main__":
    # Using the bigger map
    # Ratio 1745 / 936 = 1.864
    generate_obj(
        "web_presentation/assets/bigger_map.png", 
        "web_presentation/models/port_geo.obj",
        scale_x=500.0, # Increased scale for bigger map
        scale_z=500.0 / 1.864,
        height=5.0 
    )