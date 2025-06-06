<template>
  <div class="dashboard">
    <el-container>
    
      <el-main class="dashboard-main">
        <el-card class="dashboard-card">
          <el-tabs
            v-model="activeTab"
            type="card"
            @tab-click="handleTabClick"
            class="dashboard-tabs"
          >
            <el-tab-pane name="file-upload">
              <template #label>
                <div class="tab-label">
                  <el-icon><ElIconUpload /></el-icon>
                  <span>文件上传</span>
                </div>
              </template>
              <div class="tab-content">
                <el-row :gutter="20">
                  <!-- File Upload Column -->
                  <el-col :xs="24" :sm="24" :md="12">
                    <FileUploader
                      @upload-complete="handleUploadComplete"
                      @process-folder="handleProcessFolder"
                      @refresh-files="handleRefreshFiles"
                    />
                  </el-col>

                  <!-- File Preview Column -->
                  <el-col :xs="24" :sm="24" :md="12">
                    <FilePreview
                      :selectedFile="selectedFile"
                      :fileList="$refs.fileListComponent ? $refs.fileListComponent.files : []"
                      @select-file="handleFileSelected"
                    />
                  </el-col>
                </el-row>

                <!-- File List Section -->
                <div class="file-list-section">
                  <FileList
                    ref="fileListComponent"
                    :selectedFile="selectedFile"
                    @file-selected="handleFileSelected"
                    @preview-file="handleFileSelected"
                    @folder-selected="handleFolderSelected"
                    @process-folder="handleProcessFolder"
                  />
                </div>
              </div>
            </el-tab-pane>

            <el-tab-pane name="point-cloud">
              <template #label>
                <div class="tab-label">
                  <el-icon><ElIconConnection /></el-icon>
                  <span>点云处理</span>
                </div>
              </template>
              <div class="tab-content">
                <PointCloudProcessor />
              </div>
            </el-tab-pane>

            <el-tab-pane name="training">
              <template #label>
                <div class="tab-label">
                  <el-icon><ElIconSetting /></el-icon>
                  <span>训练</span>
                </div>
              </template>
              <div class="tab-content">
                <TrainingComponent />
              </div>
            </el-tab-pane>

            <el-tab-pane name="visualization">
              <template #label>
                <div class="tab-label">
                  <el-icon><ElIconView /></el-icon>
                  <span>训练可视化</span>
                </div>
              </template>
              <div class="tab-content">
                <TrainingVisualizationComponent />
              </div>
            </el-tab-pane>
          </el-tabs>
        </el-card>
      </el-main>
    </el-container>
  </div>
</template>

<script>
import axios from 'axios'
// SocketIOClient import removed
import FileUploader from '@/components/FileUploader.vue';
import FileList from '@/components/FileList.vue';
import FilePreview from '@/components/FilePreview.vue';
import PointCloudProcessor from '@/components/PointCloudProcessor.vue';
import TrainingComponent from '@/components/TrainingComponent.vue';
import TrainingVisualizationComponent from '@/components/RefactoredTrainingVisualization.vue';
import { eventBus } from '@/utils/eventBus';
import {
  ElContainer,
  ElHeader,
  ElMain,
  ElFooter,
  ElCard,
  ElTabs,
  ElTabPane,
  ElRow,
  ElCol,
  ElDropdown,
  ElDropdownMenu,
  ElDropdownItem,
  ElAvatar,
  ElIcon,
  ElEmpty
} from 'element-plus';
import {
  Upload as ElIconUpload,
  Connection as ElIconConnection,
  Setting as ElIconSetting,
  TrendCharts as ElIconTrendCharts,
  DataAnalysis as ElIconDataAnalysis,
  SwitchButton as ElIconSwitchButton,
  View as ElIconView
} from '@element-plus/icons-vue';

export default {
  name: 'Dashboard',
  components: {
    FileUploader,
    FileList,
    FilePreview,
    PointCloudProcessor,
    TrainingComponent,
    TrainingVisualizationComponent,
    ElContainer,
    ElHeader,
    ElMain,
    ElFooter,
    ElCard,
    ElTabs,
    ElTabPane,
    ElRow,
    ElCol,
    ElDropdown,
    ElDropdownMenu,
    ElDropdownItem,
    ElAvatar,
    ElIcon,
    ElEmpty,
    ElIconUpload,
    ElIconConnection,
    ElIconSetting,
    ElIconTrendCharts,
    ElIconDataAnalysis,
    ElIconSwitchButton,
    ElIconView
  },
  data() {
    return {
      selectedFile: null,
      activeTab: 'file-upload'
    }
  },
  computed: {
    username() {
      let username = this.$store.getters.user?.username;
      // 如果用户名是 undefined 或者为空，使用 'User'
      if (!username || username === 'undefined') {
        username = 'User';
      }
      return username;
    },
    userInitial() {
      return this.username.charAt(0).toUpperCase()
    }
  },
  mounted() {
    // 监听点云处理完成事件，自动切换到训练标签页
    eventBus.on('point-cloud-processed', this.handlePointCloudProcessed);
  },
  beforeUnmount() {
    // 移除事件监听器
    eventBus.off('point-cloud-processed', this.handlePointCloudProcessed);
  },
  methods: {
    logout() {
      this.$store.dispatch('logout')
      this.$router.push('/login')
    },

    handleTabClick(tab) {
      // 如果切换到文件上传标签页，刷新文件列表
      if (tab.props.name === 'file-upload' && this.$refs.fileListComponent) {
        this.$refs.fileListComponent.fetchFiles();
      }
    },

    handleUploadComplete() {
      // Refresh the file list when upload is complete
      this.$refs.fileListComponent.fetchFiles();
    },

    handleRefreshFiles() {
      // 刷新文件列表
      if (this.$refs.fileListComponent) {
        this.$refs.fileListComponent.fetchFiles();
      }
    },

    handleFileSelected(file) {
      this.selectedFile = file;
    },

    handleFolderSelected(folder) {
      console.log('Folder selected:', folder);

      // 如果文件夹包含图片，可以考虑自动选择第一张图片
      if (folder.has_images && folder.image_count > 0) {
        // 这里可以添加逻辑，从选定的文件夹中获取并显示第一张图片
        // 例如，可以通过API获取文件夹中的图片列表
        this.loadFolderImages(folder);
      }
    },

    async loadFolderImages(folder) {
      // 检查用户是否已登录
      if (!this.$store.getters.isAuthenticated) {
        this.$message.error('请先登录');
        return;
      }
      
      const username = this.$store.getters.user?.username;

      try {
        let response;
        
        // 尝试WebSocket获取文件列表
        try {
          if (!wsClient.isConnected) {
            await wsClient.connect('ws://localhost:6010', username);
          }
          response = await wsClient.getFiles(username);
        } catch (wsError) {
          console.warn('WebSocket获取文件失败，回退到HTTP:', wsError);
          // HTTP回退
          const httpResponse = await axios.get(`http://localhost:5000/api/files/${username}`);
          response = { data: httpResponse.data };
        }
        
        const files = response.data.files || [];

        // 过滤出属于该文件夹的图片文件
        const folderImages = files.filter(file =>
          file.folder === folder.name &&
          ['png', 'jpg', 'jpeg', 'gif'].includes(file.type.toLowerCase())
        );

        // 如果有图片，选择第一张
        if (folderImages.length > 0) {
          this.handleFileSelected(folderImages[0]);
        }
      } catch (err) {
        console.error('Error loading folder images:', err);
      }
    },

    handleProcessFolder(folderName) {
      // 切换到点云处理标签页
      this.activeTab = 'point-cloud';

      // 延迟一下，确保点云处理组件已经加载
      setTimeout(() => {
        // 触发点云处理组件的处理方法
        eventBus.emit('process-folder', folderName);
      }, 500);
    },

    // 处理点云处理完成事件
    handlePointCloudProcessed(processedData) {
      console.log('Dashboard: 点云处理完成，切换到训练标签页', processedData);

      // 刷新文件列表，确保显示最新的处理结果
      this.handleRefreshFiles();

      // 延迟一下，确保点云处理完全结束
      setTimeout(() => {
        // 切换到训练标签页
        this.activeTab = 'training';
      }, 1000);
    }
  }
}
</script>

<style scoped src="../assets/css/Dashboard.css"></style>
