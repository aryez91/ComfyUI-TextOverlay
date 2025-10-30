import torch
import torchvision.transforms.functional as TF
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os

# --- FIX FOR HEBREW STARTS HERE ---
# We need two special libraries to handle Right-to-Left text like Hebrew.
# You must install them in your ComfyUI environment.
# In your terminal/cmd, run:
# pip install python-bidi arabic_reshaper
try:
    from bidi.algorithm import get_display
    import arabic_reshaper
except ImportError:
    print("---------------------------------------------------------------------------------------------------")
    print("TextOverlay Node (Hebrew Fix): The required libraries 'python-bidi' and 'arabic_reshaper' are not installed.")
    print("Please install them by running the following command in your terminal:")
    print("pip install python-bidi arabic_reshaper")
    print("---------------------------------------------------------------------------------------------------")
    # Define dummy functions so the node doesn't crash on load
    def get_display(text): return text
    def arabic_reshaper_reshape(text): return text
else:
    # If imports are successful, alias the reshape function
    arabic_reshaper_reshape = arabic_reshaper.reshape
# --- FIX FOR HEBREW ENDS HERE ---


class TextOverlay:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "text": ("STRING", {"multiline": True, "default": "שלום עולם"}), # Added a Hebrew default
                "vertical_position": ("FLOAT", {"default": 0, "min": -1, "max": 1, "step": 0.01}),
                "text_color_option": (["White", "Black", "Red", "Green", "Blue"],),
                "bg_color_option": (["Black", "White", "Red", "Green", "Blue"],),
                "bg_opacity": ("FLOAT", {"default": 0.5, "min": 0, "max": 1, "step": 0.1}),
                # IMPORTANT: You must use a font that contains Hebrew characters.
                # NotoSansHebrew-Regular.ttf is a good free option from Google Fonts.
                "font_path": ("STRING", {"default": "C:/Windows/Fonts/Arial.ttf"}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "apply_text_overlay"
    CATEGORY = "Image Processing" # Added a category for neatness

    COLOR_OPTIONS = {
        "White": (255, 255, 255),
        "Black": (0, 0, 0),
        "Red": (255, 0, 0),
        "Green": (0, 255, 0),
        "Blue": (0, 0, 255)
    }

    def apply_text_overlay(self, image, text, vertical_position, text_color_option, bg_color_option, bg_opacity, font_path):
        # Convert torch tensor to a batch of PIL Images
        pil_images = []
        for img_tensor in image:
            img_np = img_tensor.cpu().numpy()
            img_pil = Image.fromarray((img_np * 255).astype(np.uint8))
            pil_images.append(img_pil)

        result_images = []
        for image_pil in pil_images:
            # We will draw on a copy of the image in RGBA mode to handle opacity
            overlay_image = image_pil.convert('RGBA')
            draw = ImageDraw.Draw(overlay_image)

            # --- HEBREW TEXT PROCESSING ---
            # 1. Reshape the text for complex scripts (important for Arabic, good practice for others)
            reshaped_text = arabic_reshaper_reshape(text)
            # 2. Reorder the text from logical (RTL) to visual (LTR) for rendering
            bidi_text = get_display(reshaped_text)
            # --- END HEBREW PROCESSING ---

            # Load a font
            font_size = image_pil.height // 20
            try:
                if os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, font_size)
                else:
                    print(f"Font file not found: {font_path}. Using default font.")
                    font = ImageFont.load_default()
            except Exception as e:
                print(f"Error loading font: {e}. Using default font.")
                font = ImageFont.load_default()

            # --- MODERNIZED TEXT SIZING ---
            # `draw.textsize` is deprecated. `draw.textbbox` is the modern, accurate replacement.
            text_bbox = draw.textbbox((0, 0), bidi_text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            # --- END MODERNIZED SIZING ---

            # Calculate text position
            x = (image_pil.width - text_width) // 2
            y = ((image_pil.height - text_height) // 2) + int(vertical_position * image_pil.height / 2) - text_bbox[1] # Adjust y based on bbox top

            # Draw background
            bg_color = self.COLOR_OPTIONS[bg_color_option] + (int(bg_opacity * 255),)
            bg_padding = font_size // 4 # Add padding relative to font size
            draw.rectangle(
                [x - bg_padding, y + text_bbox[1] - bg_padding, x + text_width + bg_padding, y + text_bbox[3] + bg_padding],
                fill=bg_color
            )

            # Draw text
            text_fill_color = self.COLOR_OPTIONS[text_color_option]
            draw.text((x, y), bidi_text, font=font, fill=text_fill_color)
            
            # Convert back to the original image mode (likely RGB) and append
            result_images.append(overlay_image.convert(image_pil.mode))

        # Convert the batch of PIL Images back to a torch tensor
        result_tensors = []
        for res_img in result_images:
            res_np = np.array(res_img).astype(np.float32) / 255.0
            res_tensor = torch.from_numpy(res_np)
            result_tensors.append(res_tensor)

        # Stack tensors to create the final batch
        final_tensor = torch.stack(result_tensors)

        return (final_tensor,)


NODE_CLASS_MAPPINGS = {"TextOverlay": TextOverlay}
NODE_DISPLAY_NAME_MAPPINGS = {"TextOverlay": "Add Text Overlay (Hebrew Fixed)"}
