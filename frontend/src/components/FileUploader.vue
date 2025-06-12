<template>
  <div class="file-uploader">
    <el-card class="uploader-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span class="header-title">
            <el-icon><Upload /></el-icon> 上传文件
          </span>
        </div>
      </template>

      <el-alert
        v-if="error"
        :title="error"
        type="error"
        show-icon
        :closable="true"
        @close="error = null"
      />

      <el-alert
        v-if="success"
        :title="success"
        type="success"
        show-icon
        :closable="true"
        @close="success = null"
      />

      <el-tabs v-model="activeTab" class="upload-tabs" @tab-click="handleTabClick">
        <el-tab-pane label="Video Frames" name="single">
          <template #label>
            <span>
              <el-icon><VideoCamera /></el-icon> 视频上传
            </span>
          </template>
        </el-tab-pane>
        <el-tab-pane label="Image Files" name="multiple">
          <template #label>
            <span>
              <el-icon><Picture /></el-icon> 图片上传
            </span>
          </template>
        </el-tab-pane>
        <el-tab-pane label="Folder" name="folder">
          <template #label>
            <span>
              <el-icon><Folder /></el-icon> 文件夹上传
            </span>
          </template>
        </el-tab-pane>
        <el-tab-pane label="Point Cloud" name="pointcloud">
          <template #label>
            <span>
              <el-icon><Connection /></el-icon> 点云文件
            </span>
          </template>
        </el-tab-pane>
      </el-tabs>

      <div class="tab-content">
        <!-- Video Upload with Frame Extraction -->
        <div v-if="activeTab === 'single'" class="upload-form-container">
          <el-form label-position="top">
            <el-form-item label="选择本地视频文件上传">
              <el-upload
                class="upload-demo"
                drag
                action="#"
                :auto-upload="false"
                :on-change="handleSingleFileChange"
                :file-list="singleFile ? [singleFile] : []"
                accept="video/mp4,video/x-m4v,video/*"
                ref="singleFileUpload"
              >
                <el-icon class="el-icon--upload"><upload-filled /></el-icon>
                <div class="el-upload__text">拖拽上传或者 <em>点击上传</em></div>
              </el-upload>

              <el-alert
                v-if="!isVideoFile && singleFile"
                title="Please select a video file. Only video formats are supported in this tab."
                type="warning"
                show-icon
                :closable="false"
                style="margin-top: 10px;"
              />

              <div class="upload-tip">
                <el-text type="info">Supported video formats: MP4, AVI, MOV</el-text>
              </div>
            </el-form-item>

            <el-form-item label="Custom folder name (optional)">
              <el-input
                v-model="customVideoFolderName"
                placeholder="Enter a custom folder name"
                clearable
              >
                <template #prefix>
                  <el-icon><folder /></el-icon>
                </template>
              </el-input>
              <el-text type="info" class="form-tip">
                If left empty, a folder will be created with the format: <strong>YYYY-MM-DD_HH-MM-SS_video</strong>
              </el-text>
            </el-form-item>

            <el-divider content-position="left">
              <el-text type="primary">帧率提取选项</el-text>
            </el-divider>

            <el-form-item label="Frame Rate (frames per second)">
              <el-slider
                v-model="frameRate"
                :min="1"
                :max="30"
                :step="1"
                show-input
                :format-tooltip="value => `${value} fps`"
              />
              <el-text type="info" class="form-tip">
                Higher frame rates capture more detail but create more files.
              </el-text>
            </el-form-item>

            <el-form-item>
              <el-checkbox v-model="extractAllFrames" label="Extract all frames (ignores frame rate setting)" />
              <el-text type="warning" class="form-tip" v-if="extractAllFrames">
                Warning: This may create a large number of files for longer videos.
              </el-text>
            </el-form-item>

            <el-form-item class="upload-button-container">
              <el-button
                type="primary"
                :loading="uploading"
                @click="uploadSingleFile"
                :disabled="!singleFile || !isVideoFile"
                size="large"
              >
                {{ uploading ? 'Uploading...' : 'Upload Video' }}
              </el-button>
            </el-form-item>
          </el-form>

          <el-progress
            v-if="singleFileProgress > 0 && singleFileProgress < 100"
            :percentage="singleFileProgress"
            :format="percent => `${percent}%`"
            status="primary"
            striped
            striped-flow
            class="upload-progress"
          />
        </div>

        <!-- Multiple Files Upload (Images Only) -->
        <div v-if="activeTab === 'multiple'" class="upload-form-container">
          <el-form label-position="top">
            <el-form-item label="Select multiple images to upload">
              <el-upload
                class="upload-demo"
                drag
                action="#"
                :auto-upload="false"
                :on-change="handleMultipleFilesChange"
                :file-list="multipleFiles"
                multiple
                accept="image/png,image/jpeg,image/jpg,image/gif"
                ref="multipleFilesUpload"
              >
                <el-icon class="el-icon--upload"><picture /></el-icon>
                <div class="el-upload__text">Drop images here or <em>click to upload</em></div>
                <template #tip>
                  <div class="el-upload__tip">
                    <el-text type="info">Hold Ctrl (or Cmd) to select multiple files</el-text>
                  </div>
                </template>
              </el-upload>

              <el-alert
                v-if="invalidImageFiles.length > 0"
                :title="`${invalidImageFiles.length} file(s) will be ignored because they are not images.`"
                type="warning"
                show-icon
                :closable="false"
                style="margin-top: 10px;"
              />

              <div class="upload-tip">
                <el-text type="info">Supported image formats: PNG, JPG, JPEG, GIF</el-text>
              </div>
            </el-form-item>

            <el-form-item label="Custom folder name (optional)">
              <el-input
                v-model="customImagesFolderName"
                placeholder="Enter a custom folder name"
                clearable
              >
                <template #prefix>
                  <el-icon><folder /></el-icon>
                </template>
              </el-input>
              <el-text type="info" class="form-tip">
                If left empty, a folder will be created with the format: <strong>YYYY-MM-DD_HH-MM-SS_images</strong>
              </el-text>
            </el-form-item>

            <el-form-item class="upload-button-container">
              <el-button
                type="primary"
                :loading="uploading"
                @click="uploadMultipleFiles"
                :disabled="!validImageFiles.length"
                size="large"
              >
                {{ uploading ? 'Uploading...' : 'Upload Images' }}
              </el-button>
            </el-form-item>
          </el-form>

          <el-progress
            v-if="multipleFilesProgress > 0 && multipleFilesProgress < 100"
            :percentage="multipleFilesProgress"
            :format="percent => `${percent}%`"
            status="primary"
            striped
            striped-flow
            class="upload-progress"
          />
        </div>

        <!-- Folder Upload -->
        <div v-if="activeTab === 'folder'" class="upload-form-container">
          <el-form label-position="top">
            <el-form-item label="选择文件夹类型">
              <el-radio-group v-model="folderType">
                <el-radio-button label="images">待处理图片文件夹</el-radio-button>
                <el-radio-button label="point_cloud">预处理点云文件夹</el-radio-button>
              </el-radio-group>
              <div class="form-tip">
                <el-text type="info">
                  - <strong>待处理图片文件夹</strong>: 包含需要被COLMAP处理的图片序列。
                  <br/>
                  - <strong>预处理点云文件夹</strong>: 包含可直接渲染的.ply或.splat文件。
                </el-text>
              </div>
            </el-form-item>

            <el-form-item label="选择要上传的文件夹">
              <el-upload
                class="upload-demo"
                action="#"
                :auto-upload="false"
                :on-change="handleFolderChange"
                :file-list="folderFiles"
                ref="folderUpload"
              >
                <el-button type="primary">Select Folder</el-button>
                <template #tip>
                  <div class="el-upload__tip">
                    <el-text type="info">Please select a folder to upload</el-text>
                  </div>
                </template>
              </el-upload>

              <div class="folder-upload-note">
                <el-alert
                  type="info"
                  show-icon
                  :closable="false"
                >
                  <template #title>
                    Due to browser limitations, you need to select all files in a folder.
                  </template>
                  <template #default>
                    <p>To upload a folder structure, please select all files within the folder you want to upload.</p>
                  </template>
                </el-alert>
              </div>
            </el-form-item>

            <el-form-item label="Custom folder name (optional)">
              <el-input
                v-model="customFolderName"
                placeholder="Enter a custom folder name"
                clearable
              >
                <template #prefix>
                  <el-icon><folder /></el-icon>
                </template>
              </el-input>
              <el-text type="info" class="form-tip">
                If left empty, a folder will be created with the format: <strong>YYYY-MM-DD_HH-MM-SS_folder</strong>
              </el-text>
            </el-form-item>

            <el-form-item class="upload-button-container">
              <el-button
                type="primary"
                :loading="uploading"
                @click="uploadFolder"
                :disabled="!folderFiles.length"
                size="large"
              >
                {{ uploading ? 'Uploading...' : 'Upload Folder' }}
              </el-button>
            </el-form-item>
          </el-form>

          <el-progress
            v-if="folderProgress > 0 && folderProgress < 100"
            :percentage="folderProgress"
            :format="percent => `${percent}%`"
            status="primary"
            striped
            striped-flow
            class="upload-progress"
          />
        </div>

        <!-- Point Cloud File Upload -->
        <div v-if="activeTab === 'pointcloud'" class="upload-form-container">
          <el-form label-position="top">
            <el-form-item label="选择 .ply 或 .splat 文件">
              <el-upload
                class="upload-demo"
                drag
                action="#"
                :auto-upload="false"
                :on-change="handlePointCloudFileChange"
                :file-list="pointCloudFile ? [pointCloudFile] : []"
                accept=".ply,.splat"
                ref="pointCloudFileUpload"
              >
                <el-icon class="el-icon--upload"><upload-filled /></el-icon>
                <div class="el-upload__text">拖拽上传或者 <em>点击上传</em></div>
                 <template #tip>
                  <div class="el-upload__tip">
                    <el-text type="info">支持 .ply 和 .splat 格式的点云文件</el-text>
                  </div>
                </template>
              </el-upload>
            </el-form-item>
            <el-form-item class="upload-button-container">
              <el-button
                type="primary"
                :loading="uploading"
                @click="uploadPointCloudFile"
                :disabled="!pointCloudFile"
                size="large"
              >
                {{ uploading ? '上传中...' : '上传点云文件' }}
              </el-button>
            </el-form-item>
          </el-form>
          <el-progress
            v-if="pointCloudProgress > 0 && pointCloudProgress < 100"
            :percentage="pointCloudProgress"
            status="primary"
          />
        </div>
      </div>
    </el-card>
  </div>
</template>

<script>
import axios from 'axios'
// SocketIOClient import removed
import {
  Upload,
  Folder,
  Picture,
  VideoCamera,
  UploadFilled,
  Connection,
} from '@element-plus/icons-vue';
import {
  ElTabs,
  ElTabPane
} from 'element-plus';

export default {
  name: 'FileUploader',
  components: {
    Upload,
    Folder,
    Picture,
    VideoCamera,
    UploadFilled,
    ElTabs,
    ElTabPane,
    Connection,
  },
  data() {
    return {
      singleFile: null,
      multipleFiles: [],
      folderFiles: [],
      folderPath: '',
      uploading: false,
      error: null,
      success: null,
      singleFileProgress: 0,
      multipleFilesProgress: 0,
      folderProgress: 0,
      wsClient: null,
      folderType: 'images', // 'images' or 'point_cloud'
      activeTab: 'single', // 添加当前活动标签页状态
      lastUploadedFolder: null, // 最后上传的文件夹名称
      frameRate: 5, // 默认帧率为每秒5帧
      extractAllFrames: false, // 是否提取所有帧
      customFolderName: '', // 文件夹上传的自定义文件夹名称
      customVideoFolderName: '', // 视频上传的自定义文件夹名称
      customImagesFolderName: '', // 图片上传的自定义文件夹名称
      pointCloudFile: null,
      pointCloudProgress: 0,
    }
  },
  computed: {
    isVideoFile() {
      if (!this.singleFile) return false;

      const videoTypes = ['mp4', 'avi', 'mov', 'webm', 'mkv'];
      const fileExt = this.singleFile.name.split('.').pop().toLowerCase();

      return videoTypes.includes(fileExt) || this.singleFile.type.startsWith('video/');
    },

    validImageFiles() {
      if (!this.multipleFiles.length) return [];

      return this.multipleFiles.filter(file => {
        const imageTypes = ['png', 'jpg', 'jpeg', 'gif'];
        const fileExt = file.name.split('.').pop().toLowerCase();

        return imageTypes.includes(fileExt) || file.type.startsWith('image/');
      });
    },

    invalidImageFiles() {
      if (!this.multipleFiles.length) return [];

      return this.multipleFiles.filter(file => {
        const imageTypes = ['png', 'jpg', 'jpeg', 'gif'];
        const fileExt = file.name.split('.').pop().toLowerCase();

        return !imageTypes.includes(fileExt) && !file.type.startsWith('image/');
      });
    }
  },
  methods: {
    // 处理标签页点击
    handleTabClick() {
      // 清除错误和成功消息
      this.error = null;
      this.success = null;
    },

    handleSingleFileChange(file) {
      // Element Plus 上传组件传递的是文件对象
      this.singleFile = file.raw;
      this.error = null;
      this.success = null;
      this.singleFileProgress = 0;
    },

    handleMultipleFilesChange(file, fileList) {
      // Element Plus 上传组件传递的是文件对象和文件列表
      this.multipleFiles = fileList.map(item => item.raw);
      this.error = null;
      this.success = null;
      this.multipleFilesProgress = 0;
    },

    handleFolderChange(file, fileList) {
      // Element Plus 上传组件传递的是文件对象和文件列表
      this.folderFiles = fileList.map(item => item.raw);
      this.error = null;
      this.success = null;
      this.folderProgress = 0;
      this.folderPath = fileList.length > 0 ? fileList[0].raw.webkitRelativePath.split('/')[0] : '';
    },

    handlePointCloudFileChange(file, fileList) {
      if (fileList.length > 1) {
        fileList.splice(0, 1);
      }
      const isPointCloud = file.name.endsWith('.ply') || file.name.endsWith('.splat');
      if (!isPointCloud) {
        this.$message.error('请选择 .ply 或 .splat 格式的文件');
        this.pointCloudFile = null;
        this.$refs.pointCloudFileUpload.clearFiles();
        return;
      }
      this.pointCloudFile = file;
    },

    uploadSingleFile() {
      if (!this.singleFile || !this.isVideoFile) return;

      this.uploading = true;
      this.error = null;
      this.success = null;

      const formData = new FormData();
      formData.append('file', this.singleFile);

      // 添加帧提取参数
      formData.append('extract_frames', 'true');
      formData.append('extract_all_frames', this.extractAllFrames ? 'true' : 'false');
      formData.append('frame_rate', this.frameRate.toString());

      // 添加自定义文件夹名称（如果有）
      if (this.customVideoFolderName.trim()) {
        formData.append('custom_folder_name', this.customVideoFolderName.trim());
      }

      // 检查用户是否已登录
      if (!this.$store.getters.isAuthenticated) {
        this.$message.error('请先登录');
        return;
      }

      // 使用JWT认证发送请求
      const token = this.$store.state.token;
      axios.post('http://localhost:5000/api/upload-video', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
          'Authorization': `Bearer ${token}`
        },
        withCredentials: false,
        onUploadProgress: (progressEvent) => {
          this.singleFileProgress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        }
      })
      .then(response => {
        this.success = response.data.message || 'Video uploaded and frames extracted successfully';

        // 清空上传组件
        if (this.$refs.singleFileUpload) {
          this.$refs.singleFileUpload.clearFiles();
        }

        // 保存最后上传的文件夹名称
        if (response.data.folderName) {
          this.lastUploadedFolder = response.data.folderName;
        }

        // 清空文件
        this.singleFile = null;

        // 发出上传完成事件
        this.$emit('upload-complete', {
          ...response.data
        });

        // 通知父组件刷新文件列表
        this.$emit('refresh-files');
      })
      .catch(err => {
        this.error = err.response?.data?.message || 'Video upload failed. Please try again.';
      })
      .finally(() => {
        this.uploading = false;
        setTimeout(() => {
          this.singleFileProgress = 0;
        }, 2000);
      });
    },

    uploadMultipleFiles() {
      if (!this.validImageFiles.length) return;

      this.uploading = true;
      this.error = null;
      this.success = null;

      const formData = new FormData();
      this.validImageFiles.forEach(file => {
        formData.append('files[]', file);
      });

      // 添加自定义文件夹名称（如果有）
      if (this.customImagesFolderName.trim()) {
        formData.append('custom_folder_name', this.customImagesFolderName.trim());
      }

      // 检查用户是否已登录
      if (!this.$store.getters.isAuthenticated) {
        this.$message.error('请先登录');
        return;
      }

      const username = this.$store.getters.user?.username;
      console.log('Uploading multiple files for user:', username, 'with custom folder name:', this.customImagesFolderName.trim() || '(none)');

      // 使用JWT认证发送请求
      const token = this.$store.state.token;
      // 确保自定义文件夹名称正确传递
      let url = 'http://localhost:5000/api/upload-multiple';
      if (this.customImagesFolderName.trim()) {
        url += `?custom_folder_name=${encodeURIComponent(this.customImagesFolderName.trim())}`;
      }
      console.log('Upload URL:', url);

      axios.post(url, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
          'Authorization': `Bearer ${token}`
        },
        withCredentials: false,
        onUploadProgress: (progressEvent) => {
          this.multipleFilesProgress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        }
      })
      .then(response => {
        // 显示成功消息，包括有效文件数量
        this.success = `${this.validImageFiles.length} image(s) uploaded successfully`;

        // 清空上传组件
        if (this.$refs.multipleFilesUpload) {
          this.$refs.multipleFilesUpload.clearFiles();
        }

        this.multipleFiles = [];

        // 发出上传完成事件
        this.$emit('upload-complete', {
          ...response.data
        });

        // 通知父组件刷新文件列表
        this.$emit('refresh-files');
      })
      .catch(err => {
        this.error = err.response?.data?.message || 'Image upload failed. Please try again.';
      })
      .finally(() => {
        this.uploading = false;
        setTimeout(() => {
          this.multipleFilesProgress = 0;
        }, 2000);
      });
    },

    async uploadFolder() {
      if (this.folderFiles.length === 0) {
        this.$message.error('Please select a folder first');
        return;
      }
      
      const formData = new FormData();
      this.folderFiles.forEach(file => {
        formData.append('files', file.raw, file.raw.webkitRelativePath);
      });
      
      formData.append('folder_name', this.folderPath);
      formData.append('folder_type', this.folderType); // Add folder type to form data

      this.uploading = true;
      this.error = null;
      this.success = null;
      this.folderProgress = 0;

      try {
        const username = this.$store.getters.user?.username;
        if (!username) {
          this.$message.error('User not logged in');
          this.uploading = false;
          return;
        }

        const response = await axios.post(`http://localhost:5000/api/upload_folder/${username}`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          onUploadProgress: progressEvent => {
            this.folderProgress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          }
        });

        this.success = response.data.message;

        // 清空上传组件
        if (this.$refs.folderUpload) {
          this.$refs.folderUpload.clearFiles();
        }

        // 保存最后上传的文件夹名称
        this.lastUploadedFolder = this.customFolderName.trim() || this.folderPath;

        // 清空文件列表
        this.folderFiles = [];

        // 发出上传完成事件
        this.$emit('upload-complete', {
          ...response.data,
          folderName: this.lastUploadedFolder
        });

        // 通知父组件刷新文件列表
        this.$emit('refresh-files');
      } catch (err) {
        this.error = err.response?.data?.message || 'Upload failed. Please try again.';
      } finally {
        this.uploading = false;
        setTimeout(() => {
          this.folderProgress = 0;
        }, 2000);
      }
    },

    async uploadPointCloudFile() {
      if (!this.pointCloudFile) {
        this.$message.error('Please select a point cloud file');
        return;
      }

      this.uploading = true;
      this.error = null;
      this.success = null;
      this.pointCloudProgress = 0;

      const formData = new FormData();
      formData.append('file', this.pointCloudFile.raw);

      try {
        const username = this.$store.getters.user?.username;
        if (!username) {
          this.$message.error('User not logged in');
          this.uploading = false;
          return;
        }

        const response = await axios.post(`http://localhost:5000/api/upload_point_cloud/${username}`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          onUploadProgress: progressEvent => {
            this.pointCloudProgress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          }
        });

        this.success = response.data.message;
        this.$emit('upload-complete', { file: response.data.file });
        this.$refs.pointCloudFileUpload.clearFiles();
        this.pointCloudFile = null;

      } catch (err) {
        this.error = err.response?.data?.message || 'Upload failed. Please try again.';
      } finally {
        this.uploading = false;
        setTimeout(() => {
          this.pointCloudProgress = 0;
        }, 2000);
      }
    }
  }
}
</script>

<style scoped src="../assets/styles/fileUploader.css">
@import '../assets/styles/common.css';

</style>
