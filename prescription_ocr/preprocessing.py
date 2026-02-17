"""
Image preprocessing for prescription OCR
Optimized for enhancing handwritten text readability
"""

import cv2
import numpy as np
from PIL import Image
import logging

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """Preprocess prescription images for better OCR accuracy"""
    
    def __init__(self, config=None):
        self.config = config or {}
    
    def preprocess(self, image_path):
        """
        Complete preprocessing pipeline
        
        Args:
            image_path: Path to prescription image
            
        Returns:
            preprocessed_image: Numpy array of preprocessed image
        """
        try:
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not read image: {image_path}")
            
            logger.info(f"Original image shape: {image.shape}")
            
            # Apply preprocessing steps
            image = self.resize_image(image)
            image = self.denoise(image)
            image = self.enhance_contrast(image)
            image = self.deskew(image)
            image = self.adaptive_threshold(image)
            
            logger.info(f"Preprocessed image shape: {image.shape}")
            
            return image
            
        except Exception as e:
            logger.error(f"Error preprocessing image: {e}")
            raise
    
    def resize_image(self, image, target_width=2000):
        """
        Resize image for optimal OCR
        Larger images work better for handwriting recognition
        """
        height, width = image.shape[:2]
        if width > target_width:
            scale = target_width / width
            new_width = target_width
            new_height = int(height * scale)
            image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
            logger.info(f"Resized image to {new_width}x{new_height}")
        return image
    
    def denoise(self, image):
        """Remove noise from image using Non-Local Means Denoising"""
        if len(image.shape) == 3:
            # Color image
            denoised = cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
        else:
            # Grayscale
            denoised = cv2.fastNlMeansDenoising(image, None, 10, 7, 21)
        logger.info("Applied denoising")
        return denoised
    
    def enhance_contrast(self, image):
        """
        Enhance contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)
        Very effective for improving handwriting visibility
        """
        # Convert to LAB color space
        if len(image.shape) == 3:
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
        else:
            l = image
        
        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        
        # Merge channels
        if len(image.shape) == 3:
            lab = cv2.merge([l, a, b])
            enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        else:
            enhanced = l
        
        logger.info("Enhanced contrast with CLAHE")
        return enhanced
    
    def deskew(self, image):
        """
        Correct skewed images
        Important for prescriptions that are photographed at an angle
        """
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Detect edges
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        # Detect lines using Hough transform
        lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
        
        if lines is not None and len(lines) > 0:
            # Calculate median angle
            angles = []
            for rho, theta in lines[:, 0]:
                angle = np.degrees(theta) - 90
                angles.append(angle)
            
            median_angle = np.median(angles)
            
            # Only deskew if angle is significant
            if abs(median_angle) > 0.5:
                # Rotate image
                (h, w) = image.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
                rotated = cv2.warpAffine(image, M, (w, h), 
                                        flags=cv2.INTER_CUBIC,
                                        borderMode=cv2.BORDER_REPLICATE)
                logger.info(f"Deskewed image by {median_angle:.2f} degrees")
                return rotated
        
        return image
    
    def adaptive_threshold(self, image):
        """
        Apply adaptive thresholding for better text separation
        Excellent for handwritten prescriptions with varying lighting
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Adaptive thresholding
        threshold = cv2.adaptiveThreshold(
            blurred,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,  # Block size
            2    # C constant
        )
        
        logger.info("Applied adaptive thresholding")
        return threshold
    
    def morph_operations(self, image):
        """
        Morphological operations to connect broken characters
        Useful for handwriting where strokes may be disconnected
        """
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        
        # Closing: connects nearby text
        closed = cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel, iterations=1)
        
        # Opening: removes small noise
        opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel, iterations=1)
        
        logger.info("Applied morphological operations")
        return opened
    
    def save_preprocessed(self, image, output_path):
        """Save preprocessed image"""
        cv2.imwrite(output_path, image)
        logger.info(f"Saved preprocessed image to {output_path}")


# Standalone function for quick preprocessing
def preprocess_image(image_path, output_path=None):
    """
    Quick function to preprocess an image
    
    Args:
        image_path: Input image path
        output_path: Optional output path to save preprocessed image
        
    Returns:
        preprocessed_image: Numpy array
    """
    preprocessor = ImagePreprocessor()
    preprocessed = preprocessor.preprocess(image_path)
    
    if output_path:
        preprocessor.save_preprocessed(preprocessed, output_path)
    
    return preprocessed
