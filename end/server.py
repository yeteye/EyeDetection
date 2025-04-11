import os
import zipfile
import shutil
from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename
from infer import predict_file, predict_directory
from  chatbot.chatbot import DialogueManager, VectorStore, OpenAI
from flask_cors import CORS
import uuid
import pandas as pd
import time

app = Flask(__name__)
CORS(app)  # 启用CORS以允许前端跨域请求
app.config['UPLOAD_FOLDER'] = './uploads'
app.config['RESULT_FOLDER'] = './results'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULT_FOLDER'], exist_ok=True)

def format_prediction(prediction, single=True):
    """将预测结果转换为可读的检测报告"""
    # 疾病编码到名称的映射
    disease_map = {
        'N': '正常',
        'D': '糖尿病',
        'G': '青光眼',
        'C': '白内障',
        'A': 'AMD年龄相关性黄斑变性',
        'H': '高血压视网膜病变',
        'M': '病理性近视',
        'O': '其他异常/疾病'
    }
    
    # 获取检测到的疾病
    tasks = ['N', 'D', 'G', 'C', 'A', 'H', 'M', 'O']
    detected = [disease_map[tasks[i]] for i, val in enumerate(prediction) if val == 1]
    
    # 生成结果描述
    if not detected:
        disease_desc = "未检测到明显病变"
    else:
        disease_desc = "\n".join([f"• {d}" for d in detected])

    if single == False:
        return disease_desc
    return f"""
检测结果摘要:
----------------------------------------
可能存在的眼病:
{disease_desc}
----------------------------------------

注意: 本系统提供的结果仅供参考，不能替代专业医疗诊断。
    """

# 辅助函数：检查文件是否为允许的扩展名
def allowed_file(filename, allowed_extensions):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

# 辅助函数：检查文件是否为图像文件
def is_image_file(filename):
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}
    return allowed_file(filename, allowed_extensions)

@app.route("/predict_file", methods=["POST"])
def predict_file_api():
    if 'left' not in request.files or 'right' not in request.files:
        return jsonify({"error": "Missing image files"}), 400

    left_file = request.files['left']
    right_file = request.files['right']

    left_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename("left_" + left_file.filename))
    right_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename("right_" + right_file.filename))

    left_file.save(left_path)
    right_file.save(right_path)

    prediction = predict_file(left_path, right_path)

    os.remove(left_path)
    os.remove(right_path)

    if prediction is None:
        return jsonify({"error": "Prediction failed"}), 500

    # return jsonify(prediction.tolist())
    result_text = format_prediction(prediction)
    
    return jsonify({
        'success': True,
        'result': result_text
    })

# 处理压缩包
@app.route("/predict_directory", methods=["POST"])
def predict_directory_api():
    if 'zip_file' not in request.files:
        return jsonify({"error": "Missing zip file"}), 400

    zip_file = request.files['zip_file']
    zip_filename = secure_filename(zip_file.filename)
    extract_dir = os.path.join(app.config['UPLOAD_FOLDER'], os.path.splitext(zip_filename)[0])

    os.makedirs(extract_dir, exist_ok=True)
    zip_path = os.path.join(app.config['UPLOAD_FOLDER'], zip_filename)
    zip_file.save(zip_path)

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

        df = predict_directory(extract_dir)
        csv_path = os.path.join(app.config['RESULT_FOLDER'], "batch_prediction.csv")
        df.to_csv(csv_path, index=False)
        return send_file(csv_path, mimetype='text/csv', as_attachment=True)

    except Exception as e:
        return jsonify({"error": f"Batch prediction failed: {str(e)}"}), 500

    finally:
        os.remove(zip_path)
        shutil.rmtree(extract_dir, ignore_errors=True)

# 处理手动输入路径
@app.route('/process-batch', methods=['POST'])
def process_batch():
    try:
        data = request.json
        folder_path = data.get('folder_path', '')
        
        if not folder_path or not os.path.isdir(folder_path):
            return jsonify({
                'success': False,
                'message': '无效的文件夹路径'
            }), 400
        
        # 获取子文件夹列表
        subfolders = [f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]
        
        if not subfolders:
            return jsonify({
                'success': False,
                'message': '未找到子文件夹'
            }), 400
        
        # 创建结果数据框
        results = []
        
        # 处理每个子文件夹
        for subfolder in subfolders:
            subfolder_path = os.path.join(folder_path, subfolder)
            
            # 查找左眼和右眼图片
            left_eye_path = None
            right_eye_path = None
            
            for file in os.listdir(subfolder_path):
                file_path = os.path.join(subfolder_path, file)
                if os.path.isfile(file_path):
                    lower_name = file.lower()
                    if f"{subfolder.lower()}_left" in lower_name or "left" in lower_name:
                        if is_image_file(lower_name):
                            left_eye_path = file_path
                    elif f"{subfolder.lower()}_right" in lower_name or "right" in lower_name:
                        if is_image_file(lower_name):
                            right_eye_path = file_path
            
            if left_eye_path and right_eye_path:
                # 调用眼睛疾病检测算法
                prediction = predict_file(left_eye_path, right_eye_path)
                # print(prediction)

                result_text = format_prediction(prediction, single=False)
                
                # 添加到结果列表
                results.append({
                    'folder_name': subfolder,
                    'left_eye_path': os.path.basename(left_eye_path),
                    'right_eye_path': os.path.basename(right_eye_path),
                    'result': result_text
                })
                
                # 模拟处理时间
                time.sleep(0.5)
        
        # 创建结果Excel文件
        if results:
            excel_path = os.path.join(app.config['RESULT_FOLDER'], f"eye_detection_results_{uuid.uuid4()}.xlsx")
            df = pd.DataFrame(results)
            df.to_excel(excel_path, index=False)
            
            return jsonify({
                'success': True,
                'excel_path': excel_path,
                'processed_count': len(results)
            })
        else:
            return jsonify({
                'success': False,
                'message': '未找到匹配的眼睛图片'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'处理过程中发生错误: {str(e)}'
        }), 500

@app.route('/process-batch-files', methods=['POST'])
def process_batch_files():
    temp_folder = None  # 初始化变量
    try:
        # 检查是否有文件上传
        if len(request.files) == 0:
            return jsonify({
                'success': False,
                'message': '未上传任何文件'
            }), 400
        
        # 获取文件夹名称
        folder_path = request.form.get('folder_path', '')
        if not folder_path:
            return jsonify({
                'success': False,
                'message': '未提供文件夹路径'
            }), 400
        
        # 创建临时文件夹来保存上传的文件
        session_id = str(uuid.uuid4())
        temp_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)  # 使用配置路径
        os.makedirs(temp_folder, exist_ok=True)
        
        # 保存上传的文件，保持文件夹结构
        file_paths = {}
        for key in request.files:
            file = request.files[key]
            if file and file.filename:
                # 提取相对路径
                rel_path = key
                
                # 创建目标路径
                rel_dir = os.path.dirname(rel_path)
                if rel_dir:
                    os.makedirs(os.path.join(temp_folder, rel_dir), exist_ok=True)
                
                # 保存文件
                target_path = os.path.join(temp_folder, rel_path)
                file.save(target_path)
                file_paths[rel_path] = target_path
        
        # 提取上传的文件夹结构
        folder_structure = {}
        for rel_path in file_paths:
            parts = rel_path.split('/')
            if len(parts) >= 2:  # 至少包含文件夹名和文件名
                # print(parts)
                subfolder = parts[1]
                filename = parts[-1]
                
                if subfolder not in folder_structure:
                    folder_structure[subfolder] = {'left': None, 'right': None}
                
                # 尝试识别左眼和右眼图片
                lower_filename = filename.lower()
                if f"{subfolder.lower()}_left" in lower_filename or "left" in lower_filename:
                    if is_image_file(lower_filename):
                        # print(subfolder, file_paths[rel_path])
                        folder_structure[subfolder]['left'] = file_paths[rel_path]
                elif f"{subfolder.lower()}_right" in lower_filename or "right" in lower_filename:
                    if is_image_file(lower_filename):
                        folder_structure[subfolder]['right'] = file_paths[rel_path]
        
        # 处理每个子文件夹中的图片 test
        # print("解析后的文件夹结构:")
        # for subfolder, files in folder_structure.items():
        #     print(f"{subfolder}:")
        #     print(f"  左眼文件: {files['left']}")
        #     print(f"  右眼文件: {files['right']}")

        results = []
        for subfolder, files in folder_structure.items():
            if files['left'] and files['right']:
                # 调用眼睛疾病检测算法
                predictions = predict_file(files['left'], files['right'])  
                print(predictions)
                result_text = format_prediction(predictions, single=False)
                
                # 添加到结果列表
                results.append({
                    'folder_name': subfolder,
                    'left_eye_path': os.path.basename(files['left']),
                    'right_eye_path': os.path.basename(files['right']),
                    'result': result_text
                })
                
                # 模拟处理时间
                time.sleep(0.5)
        print(results)

        # 创建结果Excel文件
        if results:
            excel_path = os.path.join(app.config['RESULT_FOLDER'], f"eye_detection_results_{uuid.uuid4()}.xlsx")  # 使用配置路径
            df = pd.DataFrame(results)
            df.to_excel(excel_path, index=False)
            
            return jsonify({
                'success': True,
                'excel_path': excel_path,
                'processed_count': len(results)
            })
        else:
            return jsonify({
                'success': False,
                'message': '未找到匹配的眼睛图片'
            }), 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'处理过程中发生错误: {str(e)}'
        }), 500
    finally:
        # 清理临时文件夹
        if temp_folder and os.path.exists(temp_folder):  # 添加存在性检查
            try:
                shutil.rmtree(temp_folder)
            except Exception as e:
                print(f"清理临时文件夹失败: {str(e)}")

@app.route('/download', methods=['GET'])
def download_file():
    try:
        file_path = request.args.get('file')
        if not file_path or not os.path.isfile(file_path):
            return jsonify({
                'success': False,
                'message': '文件不存在'
            }), 404
        
        # 获取文件名
        filename = os.path.basename(file_path)
        
        # 发送文件
        return send_file(file_path, as_attachment=True, download_name=filename)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'下载文件时发生错误: {str(e)}'
        }), 500


client = OpenAI(
    base_url="https://api.gptsapi.net/v1",
    api_key="sk-peade5e1f9308077da23d30f3d98315b9d6e6258b34uHZuT"
)

store = VectorStore.load("chatbot/vector_store/eye_disease.index",
                         "chatbot/vector_store/eye_disease_texts.pkl")
dialog = DialogueManager(client, store)

@app.route("/chat", methods=["POST"])
def chat_api():
    data = request.json
    query = data.get("query", "").strip()

    if not query:
        return jsonify({"error": "Missing query"}), 400

    try:
        response = dialog.process_query(query)
        print(f"Chatbot response: {response}")
        return jsonify({
            'success': True,
            "response": response
            })
    except Exception as e:
        return jsonify({'success': False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
