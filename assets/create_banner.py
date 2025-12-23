import cairo
import math

def create_banner():
    WIDTH = 1280
    HEIGHT = 640
    
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, WIDTH, HEIGHT)
    ctx = cairo.Context(surface)
    
    # 1. Background (Dark Theme)
    ctx.rectangle(0, 0, WIDTH, HEIGHT)
    ctx.set_source_rgb(0.12, 0.12, 0.12)  # #1E1E1E
    ctx.fill()
    
    # 2. Add subtle gradient/accents
    # Ubuntu Orange Circle
    ctx.arc(WIDTH * 0.85, HEIGHT * 0.2, 200, 0, 2 * math.pi)
    ctx.set_source_rgba(0.91, 0.33, 0.125, 0.1)  # #E95420 with low opacity
    ctx.fill()
    
    # Blue accent Circle
    ctx.arc(WIDTH * 0.1, HEIGHT * 0.9, 300, 0, 2 * math.pi)
    ctx.set_source_rgba(0.2, 0.4, 0.8, 0.1)
    ctx.fill()

    # 3. Main Text "VoxInput"
    ctx.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(120)
    
    text = "VoxInput"
    (x, y, width, height, dx, dy) = ctx.text_extents(text)
    
    # Center text
    text_x = (WIDTH - width) / 2
    text_y = (HEIGHT / 2) + (height / 2) - 40
    
    # Shadow
    ctx.move_to(text_x + 5, text_y + 5)
    ctx.set_source_rgba(0, 0, 0, 0.5)
    ctx.show_text(text)
    
    # Main Text Color (White)
    ctx.move_to(text_x, text_y)
    ctx.set_source_rgb(1, 1, 1)
    ctx.show_text(text)
    
    # 4. Subtext
    ctx.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(48)
    subtext = "Offline Voice-to-Text for Linux"
    (sx, sy, swidth, sheight, sdx, sdy) = ctx.text_extents(subtext)
    
    subtext_x = (WIDTH - swidth) / 2
    subtext_y = text_y + 80
    
    ctx.move_to(subtext_x, subtext_y)
    ctx.set_source_rgb(0.8, 0.8, 0.8)
    ctx.show_text(subtext)
    
    # 5. Badges/Decorations (Simple "Privacy First" pill)
    pill_text = "🔒 Privacy First • ⚡ Real-Time • 🐧 Open Source"
    ctx.set_font_size(24)
    (px, py, pwidth, pheight, pdx, pdy) = ctx.text_extents(pill_text)
    
    pill_x = (WIDTH - pwidth) / 2
    pill_y = subtext_y + 80
    
    ctx.move_to(pill_x, pill_y)
    ctx.set_source_rgb(0.91, 0.33, 0.125) # Orange
    ctx.show_text(pill_text)

    # Save
    output_path = "assets/voxinput_banner.png"
    surface.write_to_png(output_path)
    print(f"Banner generated at {output_path}")

if __name__ == "__main__":
    create_banner()
