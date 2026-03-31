import mss
import mss.tools
import numpy as np
import logging

logger = logging.getLogger(__name__)

class ScreenCapture:
    def __init__(self):
        self.sct = mss.mss()
        logger.debug("Initialized ScreenCapture with mss")

    def capture_region(self, x, y, width, height):
        """
        Captures a specific region of the screen.
        Returns a numpy array representing the BGRA image.
        """
        if width <= 0 or height <= 0:
            logger.warning("Invalid capture dimensions: %dx%d", width, height)
            return None

        # MSS uses top, left, width, height
        monitor = {"top": int(y), "left": int(x), "width": int(width), "height": int(height)}
        try:
            logger.info(f"Capturing region: {monitor}")
            sct_img = self.sct.grab(monitor)
            # Convert mss object to numpy array
            img = np.array(sct_img)
            # img is roughly BGRA at this point
            return img
        except Exception as e:
            logger.error(f"Error capturing screen region: {e}")
            return None
