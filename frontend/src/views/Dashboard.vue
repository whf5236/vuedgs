<template>
  <div class="dashboard">
    <el-container>
    
      <el-main class="dashboard-main">
        <div class="dashboard-container">
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
                <PointCloudProcessor ref="pointCloudProcessor" />
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

            <el-tab-pane name="gaussian-splatting">
              <template #label>
                <div class="tab-label">
                  <el-icon><ElIconView /></el-icon>
                  <span>高斯渲染</span>
                </div>
              </template>
              <div class="tab-content">
                <GaussianSplatting :selected-file="selectedFile" />
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>
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
import GaussianSplatting from '@/components/GaussianSplatting.vue';
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
    GaussianSplatting,
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
      activeTab: 'file-upload',
      isRefreshing: false,
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
  created() {
    // 确保在组件创建时就设置正确的默认标签页
    this.activeTab = 'file-upload';
  },
  mounted() {
    // 监听点云处理完成事件，自动切换到训练标签页
    eventBus.on('point-cloud-processed', this.handlePointCloudProcessed);
    
    // 确保在组件挂载后再次检查默认标签页
    this.$nextTick(() => {
      this.activeTab = 'file-upload';
    });
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

    async handleTabClick(tab) {
      if (tab.props.name === 'file-upload' && this.$refs.fileListComponent) {
        this.isRefreshing = true;
        await this.$refs.fileListComponent.refreshData();
        setTimeout(() => {
          this.isRefreshing = false;
        }, 100);
      }
    },

    handleUploadComplete(data) {
      if (this.$refs.fileListComponent) {
        this.$refs.fileListComponent.refreshData();
      }

      if (data && data.file) {
        this.selectedFile = data.file;
      }

      // If a folder or video was uploaded (after frame extraction),
      // we can automatically load it in the point cloud processor without switching tabs.
      if (data && data.folder_name) {
        console.log(`Upload complete, preparing to load folder in PointCloudProcessor: ${data.folder_name}`);
        // Use eventBus to tell PointCloudProcessor to load the folder.
        // This is more robust than using refs, as the component might not be active.
        eventBus.emit('load-folder-in-processor', data.folder_name);
      }
    },

    handleRefreshFiles() {
      // 刷新文件列表
      if (this.$refs.fileListComponent) {
        this.$refs.fileListComponent.refreshData();
      }
    },

    handleFileSelected(file) {
      this.selectedFile = file;
    },

    handleFolderSelected(folder) {
      if (this.isRefreshing) return;
      this.activeTab = 'point-cloud'
      // 确保PointCloudProcessor组件已挂载并有loadFolderByName方法
      this.$nextTick(() => {
        // 由于使用了ref，我们需要确保组件已经渲染
        if (this.$refs.pointCloudProcessor) {
          this.$refs.pointCloudProcessor.loadFolderByName(folder.name)
        } else {
          // An event bus or another state management approach would be better here.
          console.warn('PointCloudProcessor component not immediately available.')
        }
      })
    },

    handleProcessFolder(folderName) {
      this.activeTab = 'point-cloud'
      this.$nextTick(() => {
        const pointCloudProcessorInstance = this.$refs.pointCloudProcessor;
        if (pointCloudProcessorInstance && pointCloudProcessorInstance.loadFolderByName) {
          pointCloudProcessorInstance.loadFolderByName(folderName)
        } else {
          eventBus.emit('load-folder-in-processor', folderName)
        }
      })
    },

    // 处理点云处理完成事件
    handlePointCloudProcessed() {
      this.activeTab = 'training';
    }
  }
}
</script>

<style scoped src="../assets/css/Dashboard.css">

</style>
