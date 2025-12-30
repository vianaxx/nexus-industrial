from PIL import Image, ImageDraw, ImageFont
import os

def create_text_logo():
    # Settings (Tighter aspect ratio for maximum width usage)
    width = 500
    height = 100 # Reduced height to prevent vertical shrinking
    bg_color = (248, 249, 250) 
    text_main = "NEXUS INDUSTRIAL"
    text_sub = "BETA Intelligence Suite"
    
    img = Image.new('RGB', (width, height), color=bg_color)
    d = ImageDraw.Draw(img)
    
    try:
        # SUPER BOLD Font attempts
        # Try Impact or Arial Black for maximum weight
        font_main = ImageFont.truetype("arialbd.ttf", 55) 
        font_sub = ImageFont.truetype("arial.ttf", 24)
    except IOError:
        font_main = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    # Draw Text - Zero Padding Key
    # Push text to the absolute left (x=0) and top to maximize scale
    d.text((0, 5), text_main, fill=(15, 23, 42), font=font_main) 
    d.text((2, 65), text_sub, fill=(100, 116, 139), font=font_sub) 
    
    os.makedirs("assets", exist_ok=True)
    img.save("assets/sidebar_logo.png")
    print("Logo generated at assets/sidebar_logo.png")

def create_icon_logo():
    # Square Icon for "Collapsed" state
    size = 100
    bg_color = (255, 255, 255, 0) # Transparent if possible, or matches background
    # Use sidebar background color to blend in
    bg_color = (248, 249, 250)
    
    img = Image.new('RGB', (size, size), color=bg_color)
    d = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("arialbd.ttf", 80)
    except IOError:
        font = ImageFont.load_default()
        
    text = "N"
    
    # Calculate text size to center it (Basic centering)
    # PIL defaults
    d.text((20, 5), text, fill=(15, 23, 42), font=font)
    
    img.save("assets/sidebar_icon.png")
    print("Icon generated at assets/sidebar_icon.png")

if __name__ == "__main__":
    create_text_logo()
    create_icon_logo()

if __name__ == "__main__":
    create_text_logo()
