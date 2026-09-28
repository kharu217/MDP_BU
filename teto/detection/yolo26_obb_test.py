from ultralytics import YOLO
import cv2
import numpy as np

model = YOLO("yolo26m-obb.pt")
print(model.names)

# 방법 1: ultralytics 내장 시각화 (빠름)
results = model.predict(r"https://ultralytics.com/images/boats.jpg")
for result in results:
    annotated = result.plot()
    cv2.imshow("OBB", annotated)
    cv2.waitKey(0)
    cv2.destroyAllWindows()