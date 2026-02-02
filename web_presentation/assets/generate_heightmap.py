from PIL import Image, ImageFilter
import numpy as np
import scipy.ndimage as ndimage

def generate_heightmap(input_path, output_path):
    print(f"Processing {input_path}...")
    try:
        # Load and convert to Numpy
        img = Image.open(input_path).convert("RGB")
        data = np.array(img).astype(float)
        
        # --- STEP 1: SEGMENTATION (Water vs Land) ---
        # Logic: Land is grey/white (R~G~B high). Water is Blue (B > R).
        # We calculate a "Water Difference": (Blue - Red).
        # If Blue is significantly higher than Red, it's Water.
        
        R = data[:,:,0]
        G = data[:,:,1]
        B = data[:,:,2]
        
        # In the map, the water is dark blue-green. The land is bright grey.
        # Simple brightness check: Land is VERY bright (> 150 average). Water is darker (< 100).
        brightness = (R + G + B) / 3.0
        
        # Create a binary mask: 1 = Potential Land, 0 = Water
        # Threshold: Areas brighter than 110 are land/boats.
        mask = brightness > 110
        
        # --- STEP 2: REMOVE BOATS (Size Filtering) ---
        # We look for "connected components" (islands of white pixels).
        # The breakwater and cliffs are HUGE areas. Boats are small isolated islands.
        
        # Label each distinct island with a unique number
        labeled_array, num_features = ndimage.label(mask)
        
        # Calculate the size (pixel count) of each island
        sizes = ndimage.sum(mask, labeled_array, range(num_features + 1))
        
        # Filter: Only keep islands larger than X pixels.
        # Boats might be 50-500 pixels. The Breakwater is likely 50,000+ pixels.
        # Let's set a safe threshold of 2000 pixels.
        min_size = 2000
        
        # Create a boolean mask of "valid labels" (regions big enough to be land)
        mask_size = sizes < min_size
        remove_pixel = mask_size[labeled_array]
        
        # Update the mask: Set small regions to False (Water)
        mask[remove_pixel] = False
        
        # --- STEP 3: FILL HOLES ---
        # Sometimes the middle of the pier has dark spots. Fill holes in the big landmasses.
        mask = ndimage.binary_fill_holes(mask)
        
        # --- STEP 4: GENERATE FLAT HEIGHTMAP ---
        # Instead of using pixel brightness (which causes spikes), we use a flat value.
        # Land = 255 (or somewhat lower to be realistic scale), Water = 0.
        
        # Create blank heightmap
        heightmap = np.zeros_like(brightness)
        
        # Set Land to a uniform height (e.g., 200 out of 255)
        # This solves the "spikes on asphalt" problem. The pier will be perfectly flat.
        heightmap[mask] = 180 
        
        # --- STEP 5: EDGE SMOOTHING ---
        # Blur the transition so we get slopes instead of 90-degree jagged cliffs
        final_img = Image.fromarray(heightmap.astype('uint8'))
        final_img = final_img.filter(ImageFilter.GaussianBlur(radius=6))
        
        final_img.save(output_path)
        print(f"Heightmap saved to {output_path}")
        print(f"Removed {num_features} detected objects (boats/noise). Kept large landmasses.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    generate_heightmap("web_presentation/assets/map_baleeira.png", "web_presentation/assets/heightmap_baleeira.png")
