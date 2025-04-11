import os
import numpy as np
import pandas as pd
from PIL import Image
import onnxruntime as ort
import torch
from torchvision import transforms

tasks = ['N', 'D', 'G', 'C', 'A', 'H', 'M', 'O']

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# 配置ONNX Runtime
providers = ['CUDAExecutionProvider' if torch.cuda.is_available() else 'CPUExecutionProvider']
ort_session = ort.InferenceSession("./models/dual_focal.onnx", providers=providers)

def predict_file(left_path, right_path):
    """处理单个文件的预测"""
    if not (os.path.exists(left_path) and os.path.exists(right_path)):
        print("Warning: Missing images")
        return None
    def process_image(path):
        img = Image.open(path).convert('RGB')
        return transform(img).unsqueeze(0).numpy()  # 添加batch维度并转为numpy
    
    left_np = process_image(left_path)
    right_np = process_image(right_path)

    # 执行推理
    outputs = ort_session.run(
        None, 
        {
            "left_input": left_np,
            "right_input": right_np
        }
    )[0]

    probs = 1 / (1 + np.exp(-outputs))  # sigmoid
    predictions = (probs > 0.5).astype(int)
    return predictions[0]

def predict_folder(folder_path):
    """处理单个文件夹的预测"""
    folder_name = os.path.basename(folder_path)
    left_filename = f"{folder_name}_left.jpg"
    right_filename = f"{folder_name}_right.jpg"
    left_path = os.path.join(folder_path, left_filename)
    right_path = os.path.join(folder_path, right_filename)
    
    predictions = predict_file(left_path, right_path)
    return predictions, os.path.basename(folder_path)

def predict_directory(root_dir):
    """处理整个目录的预测"""
    results = []
    folders = [d for d in os.listdir(root_dir) if os.path.isdir(os.path.join(root_dir, d))]
    
    for folder in folders:
        folder_path = os.path.join(root_dir, folder)
        pred, folder_name = predict_folder(folder_path)
        if pred is not None:
            results.append({
                "folder": folder_name,
                **dict(zip(tasks, pred))
            })
    
    return pd.DataFrame(results)

if __name__ == "__main__":
    '''
    输入目录结构示例：
    /path/to/root_dir
    ├── 001
    │   ├── 001_left.jpg
    │   └── 001_right.jpg
    ├── 002
    │   ├── 002_left.jpg
    │   └── 002_right.jpg
    '''
    
    # prediction =  predict_file("./test/937/937_left.jpg", "./test/937/937_right.jpg")
    prediction = predict_folder("./test/937")
    # prediction = predict_directory("./test")
    print(prediction)
    # root_dir = "/path/to/your/images/root_directory"
    # result_df = predict_directory(root_dir)
    
    # # 保存结果
    # result_df.to_csv("onnx_predictions.csv", index=False)
    # print("预测结果已保存到 onnx_predictions.csv")