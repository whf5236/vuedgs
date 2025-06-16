<template>
  <div class="file-list glass-card">
    <div class="card-header">
      <div class="header-title">
        <el-icon><Folder /></el-icon> 已经上传的数据
        <el-tag v-if="$store.getters.user" size="small" type="info" class="username-tag">
          {{ $store.getters.user.username }}
        </el-tag>
      </div>
      <div>
        <el-button type="primary" size="small" @click="refreshData" :icon="Refresh" class="glass-button">
          刷新
        </el-button>
      </div>
    </div>

    <!-- Loading State -->
    <el-skeleton v-if="loading" :rows="6" animated />

    <!-- Error State -->
    <el-result
      v-else-if="error"
      icon="error"
      :title="error"
    >
      <template #extra>
        <el-button type="primary" @click="refreshData">
          <el-icon><Refresh /></el-icon> 再次尝试
        </el-button>
      </template>
    </el-result>

    <!-- Folders and Files View -->
    <div v-else>
      <el-empty
        v-if="!displayedItems.length"
        description="No files or folders found. Upload some data to get started."
      >
        <template #image>
          <el-icon class="empty-icon"><FolderOpened /></el-icon>
        </template>
      </el-empty>

      <div v-else>
        <!-- Filter Options -->
        <div class="folder-options">
          <el-select v-model="sortOption" placeholder="Sort by" size="small">
            <el-option label="Newest first" value="date-desc" />
            <el-option label="Oldest first" value="date-asc" />
            <el-option label="Name (A-Z)" value="name-asc" />
            <el-option label="Name (Z-A)" value="name-desc" />
          </el-select>
          <el-tag type="info">{{ displayedItems.length }} item(s)</el-tag>
        </div>

        <!-- Items Grid -->
        <div class="folder-grid">
          <div
            v-for="item in displayedItems"
            :key="item.name"
            class="folder-card glass-card-inner"
            :class="{
              'folder-selected': (item.item_type === 'folder' && selectedFolder === item.name) || (item.item_type === 'file' && selectedFile && selectedFile.name === item.name)
            }"
            @click="selectItem(item)"
          >
            <div class="folder-content">
              <div class="folder-icon">
                <!-- Folder Icon -->
                <template v-if="item.item_type === 'folder'">
                  <el-icon v-if="item.type === 'point_cloud'" color="#67C23A" size="30">
                    <ElIconConnection />
                  </el-icon>
                  <el-icon v-else :color="item.has_images ? '#409EFF' : '#909399'" size="30">
                    <Folder />
                  </el-icon>
                </template>
                <!-- File Icon -->
                <template v-else>
                   <el-icon color="#A8A8A8" size="30"><Files /></el-icon>
                </template>
              </div>
              <div class="folder-info">
                <div class="folder-name" :title="item.name">{{ item.name }}</div>
                <div class="folder-meta">
                  <!-- Folder Meta -->
                  <template v-if="item.item_type === 'folder'">
                    <el-tag size="small" :type="item.type === 'point_cloud' ? 'success' : 'info'">
                      {{ item.type === 'point_cloud' ? 'Point Cloud' : 'Images' }}
                    </el-tag>
                    <el-tag v-if="item.has_images" size="small" type="info" class="image-count">
                      <el-icon><Picture /></el-icon> {{ item.image_count }}
                    </el-tag>
                  </template>
                   <!-- File Meta -->
                  <template v-else>
                     <el-tag size="small" type="warning">{{ formatFileSize(item.size) }}</el-tag>
                  </template>
                  <div class="folder-date">{{ formatDate(item.created_time) }}</div>
                </div>
              </div>
              <div class="folder-actions">
                <el-button
                  v-if="item.item_type === 'folder' && item.type !== 'point_cloud' && item.has_images"
                  type="primary"
                  size="small"
                  circle
                  @click.stop="processFolder(item)"
                  :icon="Histogram"
                  title="Process for point cloud"
                />
                <el-button
                  type="danger"
                  size="small"
                  circle
                  @click.stop="confirmDeleteFolder(item)"
                  :icon="Delete"
                  title="Delete folder"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
// SocketIOClient import removed
import { eventBus } from '@/utils/eventBus';
import { TrainingService } from '@/services/trainingService';
import { markRaw } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import {
  Folder,
  FolderOpened,
  Picture,
  Refresh,
  Histogram,
  Connection as ElIconConnection,
  Files,
  Delete,
} from '@element-plus/icons-vue';

export default {
  name: 'FileList',
  components: {
    Folder,
    FolderOpened,
    Picture,
    Refresh,
    Histogram,
    ElIconConnection,
    Files,
    Delete,
  },
  props: {
    selectedFile: {
      type: Object,
      default: null
    },
    filterProcessed: {
      type: Boolean,
      default: true
    }
  },
  data() {
    return {
      files: [],
      folders: [],
      processedFolders: [],
      loading: true,
      error: null,
      selectedFolder: null,
      folderSortOption: 'date-desc',
      sortOption: 'date-desc',
      Refresh: markRaw(Refresh),
      Histogram: markRaw(Histogram),
      Delete: markRaw(Delete)
    }
  },
  computed: {
    displayedItems() {
      const folders = (this.folders || []).map(f => ({ ...f, item_type: 'folder' }));
      // 根据用户要求，不再显示根目录下的独立文件
      // const rootFiles = (this.files || []).map(f => ({ ...f, item_type: 'file' }));
      const combined = [...folders];

      return combined.sort((a, b) => {
        switch (this.sortOption) {
          case 'date-desc':
            return b.created_time - a.created_time;
          case 'date-asc':
            return a.created_time - b.created_time;
          case 'name-asc':
            return a.name.localeCompare(b.name);
          case 'name-desc':
            return b.name.localeCompare(a.name);
          default:
            return 0;
        }
      });
    },
    sortedFolders() {
      if (!this.folders.length) return [];

      const sortedFolders = [...this.folders];

      switch (this.folderSortOption) {
        case 'date-desc':
          return sortedFolders.sort((a, b) => b.created_time - a.created_time);
        case 'date-asc':
          return sortedFolders.sort((a, b) => a.created_time - b.created_time);
        case 'name-asc':
          return sortedFolders.sort((a, b) => a.name.localeCompare(b.name));
        case 'name-desc':
          return sortedFolders.sort((a, b) => b.name.localeCompare(a.name));
        case 'images-desc':
          return sortedFolders.sort((a, b) => b.image_count - a.image_count);
        default:
          return sortedFolders;
      }
    }
  },
  emits: ['file-selected', 'preview-file', 'folder-selected'],
  mounted() {
    this.fetchData();
    this.fetchProcessedFolders();

    eventBus.on('refresh-folders', this.handleRefreshFolders);
  },

  beforeUnmount() {
    eventBus.off('refresh-folders', this.handleRefreshFolders);
  },
  methods: {
    fetchData() {
      this.loading = true;
      this.error = null;

      const user = this.$store.getters.user;

      if (!user || !user.username) {
        this.error = 'Please log in to view your files.';
        this.loading = false;
        return;
      }

      if (!this.$store.getters.isAuthenticated) {
        this.$message.error('请先登录');
        return;
      }
      
      const username = user.username;
      console.log('Fetching data for user:', username);

      this.fetchFolders(username);

      this.fetchFiles(username);
    },

    async fetchFolders(username) {
      try {
        const timestamp = new Date().getTime();
        const response = await axios.get(`http://localhost:5000/api/folders/${username}?_=${timestamp}`);
        
        this.folders = response.data.folders || [];
        console.log('Folders loaded:', this.folders);

        if (this.processedFolders.length > 0) {
          this.filterProcessedFolders();
        }

        if (this.folders.length > 0 && !this.selectedFolder) {
          this.selectFolder(this.folders[0]);
        }
      } catch (err) {
        console.error('Error fetching folders:', err);
        this.handleError(err);
      } finally {
        if (this.folders.length > 0 && !this.loading) {
          this.loading = false;
        }
      }
    },

    async fetchFiles(username) {
      try {
        const timestamp = new Date().getTime();
        const response = await axios.get(`http://localhost:5000/api/files/${username}?_=${timestamp}`);
        
        this.files = response.data.files || [];
        console.log('Files loaded:', this.files);

        if (this.files.length > 0 && !this.selectedFile) {
          this.selectFile(this.files[0]);
        }
      } catch (err) {
        console.error('Error fetching files:', err);
        this.handleError(err);
      } finally {
        this.loading = false;
      }
    },

    handleError(err) {
      if (err.response) {
        if (err.response.status === 403) {
          this.error = 'You do not have permission to access these files.';
        } else if (err.response.status === 404) {
          this.error = 'User directory not found. Please upload some files first.';
        } else {
          this.error = `Error: ${err.response.data.message || 'Failed to load data'}`;
        }
      } else if (err.request) {
        this.error = 'Server not responding. Please check your connection and try again.';
      } else {
        this.error = 'Failed to load data. Please try again later.';
      }
      console.error('Detailed error:', err);
    },

    refreshData() {
      this.loading = true;
      this.fetchData();
      this.fetchProcessedFolders();
    },

    handleRefreshFolders() {
      console.log('Received refresh-folders event');
      this.refreshData();
    },

    async fetchProcessedFolders() {
      try {
        const username = this.$store.getters.user?.username;
        if (!username) {
            console.warn('获取已处理文件夹时用户名为空');
            return;
        }
        
        const response = await TrainingService.getPointCloudResults(username);
        
        if (response && Array.isArray(response.results)) {
          this.processedFolders = response.results.map(r => r.folder_name);
          console.log('已处理的原始文件夹:', this.processedFolders);
          
          this.filterProcessedFolders();
        } else {
          this.processedFolders = [];
          console.warn('Point cloud results is not an array or missing:', response);
        }
      } catch (err) {
        console.error('获取已处理文件夹列表失败:', err);
        this.processedFolders = [];
      }
    },

    filterProcessedFolders() {
      if (!this.filterProcessed) {
        console.log('Filtering of processed folders is disabled.');
        return;
      }
      if (this.processedFolders.length === 0) return;

      const originalCount = this.folders.length;

      this.folders = this.folders.filter(folder => {
        const shouldKeep = !this.processedFolders.includes(folder.name);
        if (!shouldKeep) {
          console.log(`文件夹 ${folder.name} 是否保留: ${shouldKeep}`);
        }
        return shouldKeep;
      });

      console.log(`过滤前文件夹数量: ${originalCount}, 过滤后: ${this.folders.length}`);
    },

    selectItem(item) {
      if (item.item_type === 'folder') {
        this.selectFolder(item);
      } else {
        this.selectFile(item);
      }
    },

    selectFolder(folder) {
      this.selectedFolder = folder.name;
      this.$emit('folder-selected', folder);

      if (folder.has_images && folder.image_count > 0) {
        this.loadFolderImages(folder);
      }
    },

    processFolder(folder) {
      if (!folder.has_images) return;

      this.$emit('process-folder', folder.name);
    },

    loadFolderImages(folder) {
      const folderImages = this.files.filter(file =>
        file.folder === folder.name &&
        ['png', 'jpg', 'jpeg', 'gif'].includes(file.type.toLowerCase())
      );

      if (folderImages.length > 0) {
        this.selectFile(folderImages[0]);
      }
    },

    getFileIcon(type) {
      const iconMap = {
        'png': 'fas fa-file-image text-info',
        'jpg': 'fas fa-file-image text-info',
        'jpeg': 'fas fa-file-image text-info',
        'gif': 'fas fa-file-image text-info',
        'mp4': 'fas fa-file-video text-danger',
        'avi': 'fas fa-file-video text-danger',
        'mov': 'fas fa-file-video text-danger',
        'webm': 'fas fa-file-video text-danger',
        'mkv': 'fas fa-file-video text-danger',
        'zip': 'fas fa-file-archive text-warning',
        'rar': 'fas fa-file-archive text-warning',
        '7z': 'fas fa-file-archive text-warning',
        'unknown': 'fas fa-file text-muted'
      };

      return iconMap[type.toLowerCase()] || iconMap.unknown;
    },

    getFileName(path) {
      return path.split('/').pop();
    },

    formatFileSize(bytes) {
      if (bytes === 0) return '0 Bytes';

      const k = 1024;
      const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));

      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    formatDate(timestamp) {
      if (!timestamp) return '';

      const date = new Date(timestamp * 1000);
      return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    },

    getFileUrl(path) {
      const token = localStorage.getItem('token');
      return `http://localhost:5000${path}?token=${token}`;
    },

    selectFile(file) {
      this.selectedFolder = null;
      this.$emit('file-selected', file);
    },

    previewFile(file) {
      this.$emit('preview-file', file);
    },

    async confirmDeleteFolder(folder) {
      try {
        await ElMessageBox.confirm(
          `您确定要永久删除文件夹 "${folder.name}" 及其所有内容吗？此操作不可逆。`,
          '警告',
          {
            confirmButtonText: '确定删除',
            cancelButtonText: '取消',
            type: 'warning',
          }
        );
        this.deleteFolder(folder);
      } catch (e) {
        ElMessage({
          type: 'info',
          message: '删除操作已取消',
        });
      }
    },

    async deleteFolder(folder) {
      const username = this.$store.getters.user?.username;
      if (!username) {
        ElMessage.error('无法获取用户信息，请重新登录。');
        return;
      }
      try {
        await axios.delete(`http://localhost:5000/api/folders/${username}/${folder.name}`);
        ElMessage.success(`文件夹 "${folder.name}" 已成功删除。`);
        this.refreshData();
      } catch (err) {
        console.error('删除文件夹失败:', err);
        const errorMessage = err.response?.data?.message || '删除失败，请稍后重试。';
        ElMessage.error(errorMessage);
      }
    },
  }
}
</script>

<style scoped>
.glass-card {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(5px);
  border-radius: 15px;
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #fff;
  height: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
}

.header-title {
  font-size: 1.2rem;
  font-weight: 600;
  display: flex;
  align-items: center;
}
.header-title .el-icon {
  margin-right: 8px;
}
.username-tag {
  margin-left: 10px;
  background-color: rgba(0,0,0,0.2);
  border-color: rgba(255,255,255,0.2);
  color: #eee;
}

.glass-button {
  background-color: rgba(78, 115, 223, 0.5) !important;
  border-color: rgba(78, 115, 223, 0.8) !important;
  color: #fff !important;
}
.glass-button:hover {
  background-color: rgba(78, 115, 223, 0.7) !important;
  border-color: #4e73df !important;
}

.folder-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}
:deep(.el-select .el-input__wrapper) {
  background-color: rgba(0,0,0,0.2) !important;
  box-shadow: none !important;
  border-radius: 6px;
}
:deep(.el-select .el-input__inner) {
  color: #fff;
}

.folder-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 15px;
}

.glass-card-inner {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 10px;
  padding: 15px;
  transition: all 0.3s ease;
  cursor: pointer;
}
.glass-card-inner:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.3);
  transform: translateY(-3px);
}
.folder-selected {
  background: rgba(78, 115, 223, 0.3);
  border-color: rgba(78, 115, 223, 0.7);
  box-shadow: 0 0 15px rgba(78, 115, 223, 0.5);
}

.folder-content {
  display: flex;
  align-items: center;
}
.folder-icon {
  margin-right: 15px;
}
.folder-info {
  flex-grow: 1;
  overflow: hidden;
}
.folder-name {
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.folder-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 5px;
}
.folder-meta :deep(.el-tag) {
  background-color: rgba(0,0,0,0.2);
  border-color: rgba(255,255,255,0.2);
  color: #eee;
}
.folder-date {
  font-size: 0.8em;
  color: #ccc;
  margin-left: auto;
}
</style>