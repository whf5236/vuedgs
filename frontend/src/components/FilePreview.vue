<template>
  <div class="file-preview">
    <el-card class="preview-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span class="header-title">
            <el-icon><View /></el-icon> File Preview
          </span>
        </div>
      </template>

      <div v-if="loading" class="loading-container">
        <el-skeleton animated :rows="6" />
        <div class="loading-text">Loading preview...</div>
      </div>

      <div v-else-if="!selectedFile" class="empty-preview">
        <el-empty description="Select a file to preview">
          <template #image>
            <el-icon class="empty-icon"><Document /></el-icon>
          </template>
        </el-empty>
      </div>

      <div v-else-if="loadError" class="error-preview">
        <el-result
          icon="error"
          title="Error loading file preview"
          :sub-title="loadError"
        >
          <template #extra>
            <el-button type="primary" @click="retryLoad">
              <el-icon><RefreshRight /></el-icon> Retry
            </el-button>
          </template>
        </el-result>
      </div>

      <div v-else class="preview-container">
        <!-- 图片预览 -->
        <div v-if="isImage" class="image-preview" ref="imagePreviewContainer">
          <el-image
            :src="fileUrl"
            :style="{ transform: `scale(${zoomLevel})` }"
            @wheel.prevent="handleWheel"
            @error="handleImageError"
            @mousedown="startDrag"
            @touchstart="startDrag"
            alt="Image preview"
            class="preview-image"
            ref="previewImage"
            fit="contain"
            :preview-src-list="[fileUrl]"
            :initial-index="0"
            hide-on-click-modal
          />
        </div>

        <!-- 视频预览 -->
        <div v-else-if="isVideo" class="video-preview">
          <video controls class="preview-video" @error="handleVideoError">
            <source :src="fileUrl" :type="`video/${selectedFile.type}`">
            Your browser does not support the video tag.
          </video>
        </div>

        <!-- 其他文件类型 -->
        <div v-else class="other-file-preview">
          <el-result icon="info" :title="selectedFile.filename">
            <template #icon>
              <el-icon class="file-type-icon"><Document /></el-icon>
            </template>
            <template #sub-title>
              <span>This file type cannot be previewed</span>
            </template>
            <template #extra>
              <el-button type="primary" @click="openInNewTab">
                <el-icon><TopRight /></el-icon> Open in New Tab
              </el-button>
              <el-button type="success" @click="downloadFile">
                <el-icon><Download /></el-icon> Download
              </el-button>
            </template>
          </el-result>
        </div>
      </div>

      <!-- 图片导航按钮 -->
      <div v-if="selectedFile && isImage" class="image-navigation">
        <el-button
          circle
          @click="prevImage"
          :disabled="!hasPrevImage"
          type="primary"
          :icon="ArrowLeft"
        />
        <el-button
          circle
          @click="nextImage"
          :disabled="!hasNextImage"
          type="primary"
          :icon="ArrowRight"
        />
      </div>

      <!-- 缩放控制 -->
      <div v-if="selectedFile && isImage" class="zoom-controls-container">
        <div class="zoom-slider-container">
          <el-button
            circle
            @click="decreaseZoom"
            :icon="ZoomOut"
            size="small"
          />

          <el-slider
            v-model="zoomLevel"
            :min="0.2"
            :max="5"
            :step="0.1"
            :format-tooltip="value => `${Math.round(value * 100)}%`"
            class="zoom-slider"
          />

          <el-button
            circle
            @click="increaseZoom"
            :icon="ZoomIn"
            size="small"
          />

          <el-tag type="info" class="zoom-value">{{ Math.round(zoomLevel * 100) }}%</el-tag>

          <el-button
            circle
            @click="resetZoom"
            :icon="RefreshRight"
            size="small"
          />
        </div>
      </div>

      <el-descriptions
        v-if="selectedFile"
        :column="1"
        border
        class="file-info"
      >
        <el-descriptions-item label="Filename">{{ selectedFile.filename }}</el-descriptions-item>
        <el-descriptions-item label="Type">{{ selectedFile.type.toUpperCase() }}</el-descriptions-item>
        <el-descriptions-item label="Size">{{ formatFileSize(selectedFile.size) }}</el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script>
import {
  View,
  Document,
  RefreshRight,
  Download,
  TopRight,
  ZoomIn,
  ZoomOut,
  ArrowLeft,
  ArrowRight
} from '@element-plus/icons-vue';

export default {
  name: 'FilePreview',
  components: {
    View,
    Document,
    RefreshRight,
    Download,
    TopRight,
    ZoomIn,
    ZoomOut,
    ArrowLeft,
    ArrowRight
  },
  props: {
    selectedFile: {
      type: Object,
      default: null
    },
    fileList: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      loading: false,
      loadError: null,
      zoomLevel: 1.0, // 使用浮点数确保滑动条能正常工作
      fileUrl: null,
      authToken: localStorage.getItem('token'),
      isDragging: false,
      startX: 0,
      startY: 0,
      scrollLeft: 0,
      scrollTop: 0,
      currentIndex: -1, // 当前图片在列表中的索引
      ArrowLeft, // 图标引用
      ArrowRight,
      ZoomIn,
      ZoomOut,
      RefreshRight
    }
  },
  computed: {
    isImage() {
      if (!this.selectedFile) return false;
      const imageTypes = ['png', 'jpg', 'jpeg', 'gif'];
      return imageTypes.includes(this.selectedFile.type.toLowerCase());
    },
    isVideo() {
      if (!this.selectedFile) return false;
      const videoTypes = ['mp4', 'avi', 'mov'];
      return videoTypes.includes(this.selectedFile.type.toLowerCase());
    },
    // 图片导航相关计算属性
    imageFiles() {
      return this.fileList.filter(file => {
        const imageTypes = ['png', 'jpg', 'jpeg', 'gif'];
        return imageTypes.includes(file.type.toLowerCase());
      });
    },
    hasPrevImage() {
      return this.currentIndex > 0;
    },
    hasNextImage() {
      return this.currentIndex < this.imageFiles.length - 1;
    }
  },
  watch: {
    selectedFile(newFile) {
      if (newFile) {
        this.loadFile(newFile);
        // 更新当前索引
        this.updateCurrentIndex();
      } else {
        this.fileUrl = null;
        this.currentIndex = -1;
      }
      this.resetZoom();
    },
    fileList() {
      // 文件列表变化时更新当前索引
      this.updateCurrentIndex();
    },
    // 监听滑动条值变化
    zoomLevel(newValue, oldValue) {
      // 当滑动条值变化时，确保图片缩放正确更新
      if (newValue !== oldValue && this.$refs.imagePreviewContainer) {
        const container = this.$refs.imagePreviewContainer;

        // 计算容器中心点
        const centerX = container.clientWidth / 2;
        const centerY = container.clientHeight / 2;

        // 计算缩放比例变化
        const zoomRatio = newValue / oldValue;

        // 更新滚动位置，保持中心点不变
        const newScrollLeft = (container.scrollLeft + centerX) * zoomRatio - centerX;
        const newScrollTop = (container.scrollTop + centerY) * zoomRatio - centerY;

        // 应用新的滚动位置
        container.scrollLeft = newScrollLeft;
        container.scrollTop = newScrollTop;
      }
    }
  },
  mounted() {
    // 添加全局事件监听器
    window.addEventListener('mousemove', this.onDrag);
    window.addEventListener('mouseup', this.stopDrag);
    window.addEventListener('touchmove', this.onDrag);
    window.addEventListener('touchend', this.stopDrag);
  },
  beforeUnmount() {
    // 移除全局事件监听器
    window.removeEventListener('mousemove', this.onDrag);
    window.removeEventListener('mouseup', this.stopDrag);
    window.removeEventListener('touchmove', this.onDrag);
    window.removeEventListener('touchend', this.stopDrag);
  },
  methods: {
    loadFile(file) {
      this.loading = true;
      this.loadError = null;
      this.zoomLevel = 1.0; // 重置缩放级别

      // 构建文件URL，不再使用认证
      const baseUrl = `http://localhost:5000${file.path}`;

      // 添加时间戳防止缓存
      this.fileUrl = `${baseUrl}?t=${new Date().getTime()}`;

      // 如果是图片，预加载
      if (this.isImage) {
        const img = new Image();
        img.onload = () => {
          this.loading = false;

          // 计算初始缩放级别，使图片适应容器
          if (this.$refs.imagePreviewContainer) {
            const container = this.$refs.imagePreviewContainer;
            const containerWidth = container.clientWidth;
            const containerHeight = container.clientHeight;
            const imgWidth = img.width;
            const imgHeight = img.height;

            // 计算适合容器的缩放比例
            const widthRatio = containerWidth / imgWidth;
            const heightRatio = containerHeight / imgHeight;

            // 选择较小的比例，确保图片完全适应容器
            const fitRatio = Math.min(widthRatio, heightRatio);

            // 始终使用适合容器的缩放比例，确保图片合理显示在容器内
            // 对于大图片，fitRatio会小于1，确保缩小到适合容器
            // 对于小图片，fitRatio会大于1，允许适当放大以填充容器
            // 如果图片太小，至少放大到容器的70%
            if (fitRatio > 1.0) {
              // 小图片，适当放大，但不超过原始尺寸的2倍
              this.zoomLevel = Math.min(fitRatio, 2.0);
            } else {
              // 大图片，确保至少填充容器的70%
              this.zoomLevel = Math.max(fitRatio, 0.7);
            }

            console.log(`图片尺寸: ${imgWidth}x${imgHeight}, 容器尺寸: ${containerWidth}x${containerHeight}, 缩放比例: ${this.zoomLevel}`);

            // 重置滚动位置
            container.scrollLeft = 0;
            container.scrollTop = 0;
          }
        };
        img.onerror = (error) => {
          this.loading = false;
          this.loadError = 'Failed to load image. The file may not exist or you may not have permission to view it.';
          console.error('Failed to load image:', error);
        };
        img.src = this.fileUrl;
      } else {
        // 对于非图片文件，直接设置为已加载
        this.loading = false;
      }
    },

    retryLoad() {
      if (this.selectedFile) {
        this.loadFile(this.selectedFile);
      }
    },

    handleImageError(error) {
      this.loadError = 'Failed to load image. The file may not exist or you may not have permission to view it.';
      console.error('Image error:', error);
    },

    handleVideoError(error) {
      this.loadError = 'Failed to load video. The file may not exist or you may not have permission to view it.';
      console.error('Video error:', error);
    },

    // 缩放按钮方法
    increaseZoom() {
      if (this.zoomLevel < 5) {
        this.zoomLevel = Math.min(5, parseFloat((this.zoomLevel + 0.1).toFixed(1)));
      }
    },

    decreaseZoom() {
      if (this.zoomLevel > 0.2) {
        this.zoomLevel = Math.max(0.2, parseFloat((this.zoomLevel - 0.1).toFixed(1)));
      }
    },

    resetZoom() {
      // 重新计算适合容器的缩放级别
      if (this.isImage && this.$refs.imagePreviewContainer && this.$refs.previewImage) {
        const img = this.$refs.previewImage;
        const container = this.$refs.imagePreviewContainer;

        // 获取图片的原始尺寸
        const imgWidth = img.naturalWidth;
        const imgHeight = img.naturalHeight;

        // 获取容器尺寸
        const containerWidth = container.clientWidth;
        const containerHeight = container.clientHeight;

        // 计算适合容器的缩放比例
        const widthRatio = containerWidth / imgWidth;
        const heightRatio = containerHeight / imgHeight;

        // 选择较小的比例，确保图片完全适应容器
        const fitRatio = Math.min(widthRatio, heightRatio);

        // 始终使用适合容器的缩放比例，确保图片合理显示
        // 对于小图片，适当放大，但不超过原始尺寸的2倍
        // 对于大图片，确保至少填充容器的70%
        if (fitRatio > 1.0) {
          this.zoomLevel = Math.min(fitRatio, 2.0);
        } else {
          this.zoomLevel = Math.max(fitRatio, 0.7);
        }
      } else {
        this.zoomLevel = 1.0;
      }

      // 重置滚动位置
      if (this.$refs.imagePreviewContainer) {
        const container = this.$refs.imagePreviewContainer;
        container.scrollLeft = 0;
        container.scrollTop = 0;
      }
    },

    handleWheel(event) {
      // 计算缩放因子
      const zoomFactor = event.deltaY < 0 ? 1.1 : 0.9;

      // 应用缩放限制
      const newZoom = parseFloat((this.zoomLevel * zoomFactor).toFixed(1));
      if (newZoom >= 0.2 && newZoom <= 5) {
        // 更新滑动条值
        this.zoomLevel = newZoom;

        // 尝试保持鼠标位置不变
        if (this.$refs.imagePreviewContainer && this.$refs.previewImage) {
          const container = this.$refs.imagePreviewContainer;
          const rect = container.getBoundingClientRect();

          // 计算鼠标相对于容器的位置
          const mouseX = event.clientX - rect.left;
          const mouseY = event.clientY - rect.top;

          // 计算鼠标相对于滚动位置的百分比
          const percentX = (mouseX + container.scrollLeft) / (container.scrollWidth * this.zoomLevel / newZoom);
          const percentY = (mouseY + container.scrollTop) / (container.scrollHeight * this.zoomLevel / newZoom);

          // 更新滚动位置
          container.scrollLeft = percentX * container.scrollWidth * newZoom / this.zoomLevel - mouseX;
          container.scrollTop = percentY * container.scrollHeight * newZoom / this.zoomLevel - mouseY;
        }
      }
    },

    openInNewTab() {
      if (this.fileUrl) {
        window.open(this.fileUrl, '_blank');
      }
    },

    downloadFile() {
      if (this.fileUrl) {
        const link = document.createElement('a');
        link.href = this.fileUrl;
        link.download = this.selectedFile.filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }
    },

    formatFileSize(bytes) {
      if (bytes === 0) return '0 Bytes';

      const k = 1024;
      const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));

      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    // 图片拖动功能
    startDrag(e) {
      if (!this.isImage) return;

      // 阻止默认行为和冒泡
      e.preventDefault();
      e.stopPropagation();

      this.isDragging = true;

      // 获取鼠标/触摸起始位置
      if (e.type === 'mousedown') {
        this.startX = e.pageX;
        this.startY = e.pageY;
      } else if (e.type === 'touchstart') {
        this.startX = e.touches[0].pageX;
        this.startY = e.touches[0].pageY;
      }

      // 记录当前滚动位置
      const container = this.$refs.imagePreviewContainer;
      this.scrollLeft = container.scrollLeft;
      this.scrollTop = container.scrollTop;
    },

    onDrag(e) {
      if (!this.isDragging) return;

      // 阻止默认行为和冒泡
      e.preventDefault();
      e.stopPropagation();

      // 计算鼠标/触摸移动距离
      let x, y;
      if (e.type === 'mousemove') {
        x = e.pageX;
        y = e.pageY;
      } else if (e.type === 'touchmove') {
        x = e.touches[0].pageX;
        y = e.touches[0].pageY;
      }

      // 计算滚动距离
      const moveX = x - this.startX;
      const moveY = y - this.startY;

      // 更新滚动位置
      const container = this.$refs.imagePreviewContainer;
      container.scrollLeft = this.scrollLeft - moveX;
      container.scrollTop = this.scrollTop - moveY;
    },

    stopDrag() {
      this.isDragging = false;
    },

    // 图片导航方法
    updateCurrentIndex() {
      if (!this.selectedFile || this.imageFiles.length === 0) {
        this.currentIndex = -1;
        return;
      }

      // 查找当前文件在图片文件列表中的索引
      this.currentIndex = this.imageFiles.findIndex(file =>
        file.path === this.selectedFile.path
      );
    },

    prevImage() {
      if (!this.hasPrevImage) return;

      const prevFile = this.imageFiles[this.currentIndex - 1];
      this.$emit('select-file', prevFile);
    },

    nextImage() {
      if (!this.hasNextImage) return;

      const nextFile = this.imageFiles[this.currentIndex + 1];
      this.$emit('select-file', nextFile);
    }
  }
}
</script>

<style scoped src="../assets/styles/filePreview.css">

</style>
