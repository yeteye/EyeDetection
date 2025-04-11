from flask import Flask, request, jsonify, send_file
import os
import uuid
import pandas as pd
import time
import json
import shutil
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)  # 启用CORS以允许前端跨域请求

# 配置上传文件存储目录
UPLOAD_FOLDER = 'uploads'
RESULT_FOLDER = 'results'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

# 辅助函数：检查文件是否为允许的扩展名
def allowed_file(filename, allowed_extensions):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

# 辅助函数：检查文件是否为图像文件
def is_image_file(filename):
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}
    return allowed_file(filename, allowed_extensions)

# 需要替换的函数：处理眼睛图像并返回结果
# 辅助函数：处理眼睛图像并返回结果
def process_eye_images(left_path, right_path):
    """
    眼睛疾病检测算法函数
    实际应用中替换为真实的疾病检测逻辑
    """
    # 这里是模拟的检测结果，实际应用中应该调用真实的检测算法
    diseases = ["青光眼", "白内障", "糖尿病视网膜病变", "黄斑变性", "正常"]
    import random
    
    # 随机生成检测结果（示例用途）
    left_result = random.choice(diseases)
    right_result = random.choice(diseases)
    confidence = random.uniform(0.75, 0.99)
    
    result = f"""
检测结果摘要:
----------------------------------------
左眼状态: {left_result} (置信度: {confidence:.2f})
右眼状态: {right_result} (置信度: {confidence:.2f})
----------------------------------------

详细分析:
左眼图像分析显示可能存在{left_result}的特征。建议进一步咨询眼科医生进行确诊。
右眼图像分析显示可能存在{right_result}的特征。建议进行常规检查。

注意: 本系统提供的结果仅供参考，不能替代专业医疗诊断。
    """
    
    return result

# 处理单张图片的API
@app.route('/api/process-single', methods=['POST'])
def process_single():
    try:
        # 检查请求中是否包含必要的文件
        if 'left_eye' not in request.files or 'right_eye' not in request.files:
            return jsonify({
                'success': False,
                'message': '请上传左眼和右眼图片'
            }), 400
        
        left_eye = request.files['left_eye']
        right_eye = request.files['right_eye']
        
        # 检查文件名是否为空
        if left_eye.filename == '' or right_eye.filename == '':
            return jsonify({
                'success': False,
                'message': '未选择文件'
            }), 400
        
        # 检查文件类型
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}
        if not (allowed_file(left_eye.filename, allowed_extensions) and allowed_file(right_eye.filename, allowed_extensions)):
            return jsonify({
                'success': False,
                'message': '只允许上传图片文件 (PNG, JPG, JPEG, GIF, BMP, TIFF)'
            }), 400
        
        # 保存上传的文件
        session_id = str(uuid.uuid4())
        left_filename = secure_filename(left_eye.filename)
        right_filename = secure_filename(right_eye.filename)
        
        left_path = os.path.join(UPLOAD_FOLDER, f"{session_id}_left_{left_filename}")
        right_path = os.path.join(UPLOAD_FOLDER, f"{session_id}_right_{right_filename}")
        
        left_eye.save(left_path)
        right_eye.save(right_path)
        
        # 这里调用眼睛疾病检测算法
        # 模拟处理过程，实际应用中替换为真实的检测逻辑
        time.sleep(2)  # 模拟处理时间
        
        result = process_eye_images(left_path, right_path)
        
        return jsonify({
            'success': True,
            'result': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'处理过程中发生错误: {str(e)}'
        }), 500

# 处理手动输入路径的
@app.route('/api/process-batch', methods=['POST'])
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
                result = process_eye_images(left_eye_path, right_eye_path)
                
                # 添加到结果列表
                results.append({
                    'folder_name': subfolder,
                    'left_eye_path': os.path.basename(left_eye_path),
                    'right_eye_path': os.path.basename(right_eye_path),
                    'result': result
                })
                
                # 模拟处理时间
                time.sleep(0.5)
        
        # 创建结果Excel文件
        if results:
            excel_path = os.path.join(RESULT_FOLDER, f"eye_detection_results_{uuid.uuid4()}.xlsx")
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

@app.route('/api/process-batch-files', methods=['POST'])
def process_batch_files():
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
        temp_folder = os.path.join(UPLOAD_FOLDER, session_id)
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
                subfolder = parts[0]
                filename = parts[-1]
                
                if subfolder not in folder_structure:
                    folder_structure[subfolder] = {'left': None, 'right': None}
                
                # 尝试识别左眼和右眼图片
                lower_filename = filename.lower()
                if f"{subfolder.lower()}_left" in lower_filename or "left" in lower_filename:
                    if is_image_file(lower_filename):
                        folder_structure[subfolder]['left'] = file_paths[rel_path]
                elif f"{subfolder.lower()}_right" in lower_filename or "right" in lower_filename:
                    if is_image_file(lower_filename):
                        folder_structure[subfolder]['right'] = file_paths[rel_path]
        
        # 处理每个子文件夹中的图片
        results = []
        for subfolder, files in folder_structure.items():
            if files['left'] and files['right']:
                # 调用眼睛疾病检测算法
                result = process_eye_images(files['left'], files['right'])
                
                # 添加到结果列表
                results.append({
                    'folder_name': subfolder,
                    'left_eye_path': os.path.basename(files['left']),
                    'right_eye_path': os.path.basename(files['right']),
                    'result': result
                })
                
                # 模拟处理时间
                time.sleep(0.5)
        
        # 创建结果Excel文件
        if results:
            excel_path = os.path.join(RESULT_FOLDER, f"eye_detection_results_{uuid.uuid4()}.xlsx")
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
        if os.path.exists(temp_folder):
            try:
                shutil.rmtree(temp_folder)
            except:
                pass

@app.route('/api/download', methods=['GET'])
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

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        message = data.get('message', '')
        
        if not message:
            return jsonify({
                'success': False,
                'message': '消息内容不能为空'
            }), 400
        
        # 根据用户消息生成回复
        reply = generate_chat_reply(message)
        
        return jsonify({
            'success': True,
            'reply': reply
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'处理聊天消息时发生错误: {str(e)}'
        }), 500

# 需要替换的函数：根据用户消息生成回复
def generate_chat_reply(message):
    """
    根据用户消息生成回复的函数
    可以根据需要集成NLP或其他对话系统
    """
    # 这里是简单的关键词匹配示例，实际应用中可以使用更复杂的NLP技术
    message = message.lower()
    
    # 定义一些关键词和对应的回复
    responses = {
        '你好': '您好！我是眼睛疾病检测助手，有什么可以帮您的吗？',
        '你是谁': '我是眼睛疾病检测系统的智能助手，可以回答您关于眼睛疾病和使用本系统的问题。',
        '怎么使用': '本系统有两种模式：单张图片处理和批量处理。在单张图片处理模式下，您需要上传左眼和右眼的图片；在批量处理模式下，您可以上传包含多个子文件夹的文件夹，每个子文件夹中应包含左眼和右眼的图片。',
        '青光眼': '青光眼是一种常见的眼科疾病，主要特征是眼内压升高导致视神经损伤和视野缺损。早期诊断和治疗对于防止视力丧失非常重要。',
        '白内障': '白内障是指眼睛晶状体变得混浊，导致视力模糊。它通常随着年龄增长而发生，但也可能由外伤、某些疾病或药物引起。',
        '糖尿病视网膜病变': '糖尿病视网膜病变是糖尿病的一种常见并发症，会影响眼睛的视网膜。长期的高血糖会导致视网膜血管损伤，可能导致视力下降甚至失明。',
        '黄斑变性': '黄斑变性是一种影响视网膜中央部分（黄斑）的疾病，常导致中央视力丧失。它通常与年龄有关，也称为年龄相关性黄斑变性(AMD)。',
        '检测准确率': '我们的系统使用先进的图像处理和人工智能技术来检测眼睛疾病，但请注意，自动检测结果仅供参考，不能替代专业医生的诊断。如有疑问，请咨询眼科医生。',
        '结果怎么看': '检测结果会显示左眼和右眼的疾病预测和置信度。请注意，这只是初步筛查结果，建议由专业眼科医生进行确诊。',
        '下载结果': '在批量处理模式下，处理完成后系统会生成一个Excel文件，您可以点击"下载结果Excel"按钮下载。',
        '上传失败': '上传失败可能是因为文件格式不支持或文件太大。请确保您上传的是图片文件(PNG, JPG, JPEG, GIF, BMP, TIFF)，并且文件大小适中。',
        '谢谢': '不客气！如果您还有其他问题，随时可以向我咨询。祝您使用愉快！',
    }
    
    # 检查是否包含关键词
    for key, response in responses.items():
        if key in message:
            return response
    
    # 默认回复
    return '感谢您的提问。如果您有关于眼睛疾病检测或系统使用的问题，我很乐意为您解答。如需详细诊断，请咨询专业眼科医生。'

# 启动服务器
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)