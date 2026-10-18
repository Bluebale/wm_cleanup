import threading
from typing import Optional
from PIL import Image
import numpy as np

_LAMA_INSTANCE = None
_LOCK = threading.Lock()

def get_lama_model():
    """
    Thread-safe lazy singleton loader for AI LaMa inpainting model.
    """
    global _LAMA_INSTANCE
    if _LAMA_INSTANCE is None:
        with _LOCK:
            if _LAMA_INSTANCE is None:
                try:
                    from simple_lama_inpainting import SimpleLama
                    _LAMA_INSTANCE = SimpleLama()
                except Exception as e:
                    raise RuntimeError(
                        f"Failed to load AI LaMa neural model: {e}. "
                        "Ensure simple-lama-inpainting and torch are installed."
                    )
    return _LAMA_INSTANCE

def inpaint_with_lama(image_rgb: np.ndarray, mask_bin: np.ndarray) -> np.ndarray:
    """
    Performs AI LaMa inpainting on an RGB image and binary mask (255=inpaint, 0=keep).
    Returns RGB numpy array.
    """
    model = get_lama_model()
    pil_img = Image.fromarray(image_rgb)
    pil_mask = Image.fromarray(mask_bin, mode='L')
    
    result_pil = model(pil_img, pil_mask)
    return np.array(result_pil.convert('RGB'))
