import urllib.request
import urllib.parse
import json
import sys
sys.path.insert(0, '.')

from app.services.measurement import analyze_measurement
from fastapi import UploadFile
import io
import asyncio

async def test_measure():
    # Create a test image with a white rectangle
    import cv2
    import numpy as np
    
    test_image = np.zeros((300, 400, 3), dtype=np.uint8)
    cv2.rectangle(test_image, (50, 50), (250, 200), (255, 255, 255), -1)
    
    _, encoded = cv2.imencode('.png', test_image)
    image_bytes = encoded.tobytes()
    
    # Create a fake UploadFile
    class FakeFile:
        def __init__(self, content, filename):
            self.content = content
            self.filename = filename
            self.file = io.BytesIO(content)
        
        async def read(self):
            return self.content
    
    fake_file = FakeFile(image_bytes, 'test.png')
    
    # Test the measurement
    result = await analyze_measurement([fake_file], 'test_project', reference_width_cm=10.0)
    
    if result.images:
        img = result.images[0]
        print(f"\nImage: {img.imageName}")
        print(f"Calibration: {img.calibrationSource}")
        print(f"Pixels per cm: {img.pixelsPerCm}")
        print(f"Objects found: {len(img.objects)}")
        for obj in img.objects:
            print(f"  - {obj.name}: length={obj.length}cm, width={obj.width}cm, height={obj.height}cm")
        print(f"Background: length={img.background.length}cm, width={img.background.width}cm")
    else:
        print('No images in response')

asyncio.run(test_measure())
