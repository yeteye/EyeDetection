# 眼睛疾病检测系统

## 配置

### 前端环境配置

```cmd
npm install element-plus axios
```

### 后端环境配置

```python
conda create -n venv_name python=3.10
conda activate venv_name
pip install -r requirements.txt
```

## 需要修改的函数

在app.py中有`process_eye_images` 和 `generate_chat_reply` 函数是写死的函数需要替换成实际使用的图片处理和 `chatbot` API

## 运行指令

### 前端

进入文件夹,终端中输入

```cmd
cd fronted
npm run dev
```

### 后端

在另一个终端中启用python环境后，输入 `python app.py` 即可
