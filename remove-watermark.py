import cv2
import numpy as np
import os

# Folder paths
input_folder = r"C:\Users\Sherwin\Desktop\Karbonius_imgs"
output_folder = r"C:\Users\Sherwin\Desktop\Karbonius_imgs_cleaned"

# Ensure output folder exists
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# Process all images in the input folder
for filename in os.listdir(input_folder):
    if filename.endswith(".jpg") or filename.endswith(".png"):
        image_path = os.path.join(input_folder, filename)
        image = cv2.imread(image_path)

        if image is None:
            continue
        
        # Convert image to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Use edge detection (Canny)
        edges = cv2.Canny(gray, 50, 150)  # Adjust threshold if needed
        
        # Apply threshold to highlight watermark
        _, thresh = cv2.threshold(edges, 50, 255, cv2.THRESH_BINARY)
        
        # Find contours (possible watermark areas)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Create a mask for detected watermark
        mask = np.zeros_like(gray)
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w > 50 and h > 10:  # Filter small noise (adjust values)
                cv2.drawContours(mask, [contour], -1, (255), thickness=cv2.FILLED)

        # Inpaint to remove watermark
        inpainted_image = cv2.inpaint(image, mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)

        # Save the processed image
        output_path = os.path.join(output_folder, filename)
        cv2.imwrite(output_path, inpainted_image)

print("Automatic watermark detection and removal completed.")
