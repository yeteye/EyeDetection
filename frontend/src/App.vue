<template>
  <div class="app-container">
    <el-card class="main-card">
      <h1 class="app-title">眼睛疾病检测系统</h1>
      <el-tabs v-model="activeTab">
        <el-tab-pane label="单张图片处理" name="single">
          <div class="upload-container">
            <div class="eye-upload">
              <h3>左眼</h3>
              <el-upload
                class="upload-area"
                action="#"
                :auto-upload="false"
                :on-change="handleLeftEyeChange"
                :show-file-list="false"
                accept="image/*"
              >
                <img v-if="leftEyeUrl" :src="leftEyeUrl" class="eye-image" />
                <div v-else class="upload-placeholder">
                  <el-icon class="upload-icon"><Plus /></el-icon>
                  <div>点击上传左眼图片</div>
                </div>
              </el-upload>
            </div>
            <div class="eye-upload">
              <h3>右眼</h3>
              <el-upload
                class="upload-area"
                action="#"
                :auto-upload="false"
                :on-change="handleRightEyeChange"
                :show-file-list="false"
                accept="image/*"
              >
                <img v-if="rightEyeUrl" :src="rightEyeUrl" class="eye-image" />
                <div v-else class="upload-placeholder">
                  <el-icon class="upload-icon"><Plus /></el-icon>
                  <div>点击上传右眼图片</div>
                </div>
              </el-upload>
            </div>
          </div>
          
          <div class="action-buttons">
            <el-button type="primary" @click="processImages" :loading="processing" :disabled="!canProcess">
              {{ processing ? '处理中...' : '开始处理' }}
            </el-button>
            <el-button @click="resetSingleMode">重置</el-button>
          </div>
          
          <div v-if="processing" class="progress-section">
            <el-progress :percentage="progressPercentage" :format="progressFormat" />
          </div>
          
          <div v-if="singleResult" class="result-section">
            <h3>检测结果</h3>
            <el-input type="textarea" v-model="singleResult" :rows="5" readonly />
          </div>
        </el-tab-pane>
        
        <el-tab-pane label="批量处理" name="batch">
          <div class="batch-container">
            <h3>选择包含眼睛图像的文件夹</h3>
            <div class="folder-selection">
              <el-input v-model="folderPath" placeholder="请输入文件夹路径" class="folder-path-input" />
              <input
                type="file"
                ref="folderInput"
                webkitdirectory
                directory
                style="display: none"
                @change="handleFolderInputChange"
              />
              <el-button type="primary" @click="selectFolder">选择文件夹</el-button>
            </div>
            
            <div class="action-buttons">
              <el-button type="primary" @click="processFolder" :loading="batchProcessing" :disabled="!folderPath">
                {{ batchProcessing ? '处理中...' : '开始批量处理' }}
              </el-button>
              <el-button @click="resetBatchMode">重置</el-button>
            </div>
            
            <div v-if="batchProcessing" class="progress-section">
              <el-progress :percentage="batchProgressPercentage" :format="progressFormat" />
            </div>
            
            <div v-if="excelResult" class="result-section">
              <h3>处理完成</h3>
              <p>已成功处理 {{ processedCount }} 对眼睛图像</p>
              <el-button type="success" @click="downloadExcel">
                <el-icon><Download /></el-icon> 下载结果Excel
              </el-button>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
    
    <!-- Chatbot 浮动按钮 -->
    <div class="chatbot-container">
      <el-button 
        class="chatbot-button" 
        type="primary" 
        circle 
        @click="toggleChat"
      >
        <el-icon v-if="!chatVisible"><ChatDotRound /></el-icon>
        <el-icon v-else><Close /></el-icon>
      </el-button>
      
      <!-- 对话框 -->
      <div class="chat-panel" :class="{ 'chat-visible': chatVisible }">
        <div class="chat-header">
          <span>智能助手</span>
          <el-icon class="close-chat" @click="toggleChat"><Close /></el-icon>
        </div>
        <div class="chat-messages" ref="chatMessagesContainer">
          <div v-for="(message, index) in chatMessages" :key="index" 
              :class="['message', message.type === 'user' ? 'user-message' : 'bot-message']">
            <div class="message-content">{{ message.content }}</div>
          </div>
        </div>
        <div class="chat-input">
          <el-input 
            v-model="userMessage" 
            placeholder="请输入您的问题..." 
            :disabled="chatSending"
            @keyup.enter="sendMessage"
          />
          <el-button type="primary" :loading="chatSending" :disabled="!userMessage" @click="sendMessage">
            <span>发送</span>
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch } from 'vue';
import { Plus, Download, ChatDotRound, Close } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import axios from 'axios';

// 标签页状态
const activeTab = ref('single');

// 单张图片处理状态
const leftEyeFile = ref(null);
const rightEyeFile = ref(null);
const leftEyeUrl = ref('');
const rightEyeUrl = ref('');
const processing = ref(false);
const progressPercentage = ref(0);
const singleResult = ref('');

// 批量处理状态
const folderPath = ref('');
const folderInput = ref(null);
const selectedFiles = ref([]);
const batchProcessing = ref(false);
const batchProgressPercentage = ref(0);
const excelResult = ref(null);
const processedCount = ref(0);

// Chatbot 状态
const chatVisible = ref(false);
const userMessage = ref('');
const chatMessages = ref([
  { type: 'bot', content: '您好！我是眼睛疾病检测助手，有什么我可以帮您的吗？' }
]);
const chatSending = ref(false);
const chatMessagesContainer = ref(null);

// 计算属性
const canProcess = computed(() => {
  return leftEyeFile.value && rightEyeFile.value;
});

// 单张图片处理函数
const handleLeftEyeChange = (file) => {
  if (!file.raw.type.startsWith('image/')) {
    ElMessage.error('只能上传图片文件！');
    return;
  }
  
  leftEyeFile.value = file.raw;
  leftEyeUrl.value = URL.createObjectURL(file.raw);
  ElMessage.success('左眼图片上传成功');
};

const handleRightEyeChange = (file) => {
  if (!file.raw.type.startsWith('image/')) {
    ElMessage.error('只能上传图片文件！');
    return;
  }
  
  rightEyeFile.value = file.raw;
  rightEyeUrl.value = URL.createObjectURL(file.raw);
  ElMessage.success('右眼图片上传成功');
};

const resetSingleMode = () => {
  if (leftEyeUrl.value) URL.revokeObjectURL(leftEyeUrl.value);
  if (rightEyeUrl.value) URL.revokeObjectURL(rightEyeUrl.value);
  
  leftEyeFile.value = null;
  rightEyeFile.value = null;
  leftEyeUrl.value = '';
  rightEyeUrl.value = '';
  singleResult.value = '';
  processing.value = false;
  progressPercentage.value = 0;
  
  ElMessage.info('已重置单张图片处理');
};

const progressFormat = (percentage) => {
  return percentage === 100 ? '完成' : `${percentage}%`;
};

const processImages = async () => {
  if (!canProcess.value) {
    ElMessage.warning('请先上传左眼和右眼图片');
    return;
  }
  
  try {
    processing.value = true;
    progressPercentage.value = 10;
    
    // 创建表单数据
    const formData = new FormData();
    formData.append('left', leftEyeFile.value);
    formData.append('right', rightEyeFile.value);
    
    // 模拟进度
    const progressInterval = setInterval(() => {
      if (progressPercentage.value < 90) {
        progressPercentage.value += 10;
      }
    }, 500);
    
    try {
      // 发送请求
      const response = await axios.post('/predict_file', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      // 清除进度条模拟
      clearInterval(progressInterval);
      progressPercentage.value = 100;
      
      // 处理响应
      if (response.data.success) {
        singleResult.value = response.data.result;
        ElMessage.success('处理完成');
      } else {
        ElMessage.error(response.data.message || '处理失败');
      }
    } catch (error) {
      clearInterval(progressInterval);
      ElMessage.error('处理过程中发生错误: ' + (error.response?.data?.message || error.message));
    }
  } finally {
    processing.value = false;
  }
};

// 批量处理函数
const selectFolder = () => {
  if (folderInput.value) {
    folderInput.value.click();
  }
};

const handleFolderInputChange = (event) => {
  const files = event.target.files;
  
  if (files.length === 0) {
    return;
  }
  
  // 获取所选文件夹的名称（通过共同的父路径）
  const firstFilePath = files[0].webkitRelativePath;
  const folderName = firstFilePath.split('/')[0];
  
  folderPath.value = folderName;
  selectedFiles.value = Array.from(files);
  
  ElMessage.success(`已选择文件夹: ${folderName}，包含 ${files.length} 个文件`);
};

const resetBatchMode = () => {
  folderPath.value = '';
  selectedFiles.value = [];
  batchProcessing.value = false;
  batchProgressPercentage.value = 0;
  excelResult.value = null;
  processedCount.value = 0;
  
  // 重置文件输入框
  if (folderInput.value) {
    folderInput.value.value = '';
  }
  
  ElMessage.info('已重置批量处理');
};

const processFolder = async () => {
  if (!folderPath.value) {
    ElMessage.warning('请先输入或选择文件夹路径');
    return;
  }
  
  try {
    batchProcessing.value = true;
    batchProgressPercentage.value = 10;
    
    // 模拟进度
    const progressInterval = setInterval(() => {
      if (batchProgressPercentage.value < 90) {
        batchProgressPercentage.value += 5;
      }
    }, 800);
    
    try {
      // 准备请求数据
      let requestData;
      
      if (selectedFiles.value.length > 0) {
        // 如果有通过文件选择器选择的文件
        const formData = new FormData();
        
        // 添加文件夹路径信息
        formData.append('folder_path', folderPath.value);
        
        // 添加所有选择的文件
        selectedFiles.value.forEach(file => {
          // 使用相对路径作为 key，以保留文件夹结构
          formData.append(file.webkitRelativePath, file);
        });
        
        // 发送请求
        const response = await axios.post('/process-batch-files', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });
        
        // 处理响应
        if (response.data.success) {
          excelResult.value = response.data.excel_path;
          processedCount.value = response.data.processed_count;
          ElMessage.success('批量处理完成');
        } else {
          ElMessage.error(response.data.message || '批量处理失败');
        }
      } else {
        // 如果是手动输入的路径
        const response = await axios.post('/process-batch', {
          folder_path: folderPath.value
        });
        
        // 处理响应
        if (response.data.success) {
          excelResult.value = response.data.excel_path;
          processedCount.value = response.data.processed_count;
          ElMessage.success('批量处理完成');
        } else {
          ElMessage.error(response.data.message || '批量处理失败');
        }
      }
      
      // 清除进度条模拟
      clearInterval(progressInterval);
      batchProgressPercentage.value = 100;
      
    } catch (error) {
      clearInterval(progressInterval);
      ElMessage.error('处理过程中发生错误: ' + (error.response?.data?.message || error.message));
    }
  } finally {
    batchProcessing.value = false;
  }
};

const downloadExcel = async () => {
  if (excelResult.value) {
    try {
      // 使用 axios 请求文件并设置 responseType 为 blob
      const response = await axios.get(`/download?file=${encodeURIComponent(excelResult.value)}`, {
        responseType: 'blob'
      });
      
      // 创建 blob URL
      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      
      // 创建临时下载链接
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `眼睛疾病检测结果_${new Date().getTime()}.xlsx`);
      document.body.appendChild(link);
      
      // 触发点击下载
      link.click();
      
      // 清理
      window.URL.revokeObjectURL(url);
      document.body.removeChild(link);
      
      ElMessage.success('下载成功');
    } catch (error) {
      ElMessage.error('下载失败: ' + error.message);
    }
  }
};

// Chatbot 函数
const toggleChat = () => {
  chatVisible.value = !chatVisible.value;
  if (chatVisible.value) {
    nextTick(() => {
      scrollToBottom();
    });
  }
};

const scrollToBottom = () => {
  if (chatMessagesContainer.value) {
    chatMessagesContainer.value.scrollTop = chatMessagesContainer.value.scrollHeight;
  }
};

const sendMessage = async () => {
  if (!userMessage.value.trim() || chatSending.value) return;
  
  const message = userMessage.value;
  chatMessages.value.push({ type: 'user', content: message });
  userMessage.value = '';
  
  nextTick(() => {
    scrollToBottom();
  });
  
  chatSending.value = true;
  
  try {
    const response = await axios.post('/chat', {
      query: message
    });
    
    if (response.data.success) {
      chatMessages.value.push({ type: 'bot', content: response.data.response }); // 这里返回的是markdown格式
    } else {
      chatMessages.value.push({ type: 'bot', content: '抱歉，我无法处理您的请求。' });
    }
  } catch (error) {
    chatMessages.value.push({ type: 'bot', content: '抱歉，发生了网络错误，请稍后重试。' });
  } finally {
    chatSending.value = false;
    nextTick(() => {
      scrollToBottom();
    });
  }
};

// 监听聊天消息变化，自动滚动到底部
watch(chatMessages, () => {
  nextTick(() => {
    scrollToBottom();
  });
});
</script>

<style scoped>
.app-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.main-card {
  margin-bottom: 20px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.app-title {
  text-align: center;
  color: #409EFF;
  margin-bottom: 20px;
  font-size: 28px;
}

.upload-container {
  display: flex;
  justify-content: space-around;
  flex-wrap: wrap;
  margin-bottom: 20px;
}

.eye-upload {
  width: 45%;
  min-width: 300px;
  text-align: center;
  margin-bottom: 20px;
}

.eye-upload h3 {
  margin-bottom: 10px;
  color: #606266;
}

.upload-area {
  border: 1px dashed #d9d9d9;
  border-radius: 6px;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  height: 250px;
  display: flex;
  justify-content: center;
  align-items: center;
  transition: border-color 0.3s;
}

.upload-area:hover {
  border-color: #409EFF;
}

.upload-placeholder {
  text-align: center;
  color: #8c939d;
}

.upload-icon {
  font-size: 28px;
  margin-bottom: 8px;
}

.eye-image {
  max-width: 100%;
  max-height: 250px;
  object-fit: contain;
}

.action-buttons {
  text-align: center;
  margin: 20px 0;
}

.progress-section {
  margin: 20px 0;
}

.result-section {
  margin-top: 30px;
  padding: 15px;
  border-radius: 4px;
  background-color: #f8f8f8;
}

.folder-selection {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}

.folder-path-input {
  flex: 1;
  margin-right: 10px;
}

/* Chatbot 样式 */
.chatbot-container {
  position: fixed;
  right: 30px;
  bottom: 30px;
  z-index: 1000;
}

.chatbot-button {
  width: 60px;
  height: 60px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.chat-panel {
  position: absolute;
  bottom: 70px;
  right: 0;
  width: 350px;
  height: 500px;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: transform 0.3s, opacity 0.3s;
  transform: scale(0.9);
  opacity: 0;
  pointer-events: none;
}

.chat-visible {
  transform: scale(1);
  opacity: 1;
  pointer-events: all;
}

.chat-header {
  padding: 12px 16px;
  background-color: #409EFF;
  color: white;
  font-weight: bold;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.close-chat {
  cursor: pointer;
}

.chat-messages {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background-color: #f9f9f9;
}

.message {
  max-width: 80%;
  padding: 10px 12px;
  border-radius: 16px;
  word-break: break-word;
}

.user-message {
  align-self: flex-end;
  background-color: #e1f3ff;
  color: #333;
}

.bot-message {
  align-self: flex-start;
  background-color: #fff;
  border: 1px solid #eaeaea;
  color: #333;
}

.chat-input {
  padding: 12px;
  display: flex;
  gap: 8px;
  border-top: 1px solid #eee;
  background-color: #fff;
}

.chat-input .el-input {
  flex: 1;
}

/* 响应式布局 */
@media screen and (max-width: 768px) {
  .eye-upload {
    width: 100%;
  }
  
  .folder-selection {
    flex-direction: column;
    gap: 10px;
  }
  
  .folder-path-input {
    margin-right: 0;
    margin-bottom: 10px;
  }
  
  .chat-panel {
    width: 300px;
    height: 400px;
    right: -20px;
  }
}
</style>