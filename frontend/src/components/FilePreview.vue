<template>
  <el-card class="file-preview">
    <template #header>
      <span class="header-title">
        <el-icon><View /></el-icon> 文件预览
      </span>
    </template>

    <div v-if="loading" class="loading-container">
      <el-skeleton animated :rows="6" />
      <div class="loading-text">加载中...</div>
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
            <el-icon><RefreshRight /></el-icon> 重试
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
          @touchstart.prevent="startDrag"
          alt="Image preview"
          class="preview-image"
          ref="previewImage"
          fit="contain"
          :preview-src-list="isImage ? [fileUrl] : []"
          :initial-index="0"
          hide-on-click-modal
        />
      </div>

      <!-- 视频预览 -->
      <div v-else-if="isVideo" class="video-preview">
        <video controls class="preview-video" @error="handleVideoError">
          <source :src="fileUrl" :type="`video/${selectedFile.type}`">
          您的浏览器不支持视频标签。
        </video>
      </div>

      <!-- 其他文件类型 -->
      <div v-else class="other-file-preview">
        <el-result icon="info" :title="selectedFile.filename">
          <template #icon>
            <el-icon class="file-type-icon"><Document /></el-icon>
          </template>
          <template #sub-title>
            <span>此文件类型无法预览</span> 
          </template>
          <template #extra>
            <el-button type="primary" @click="openInNewTab">
              <el-icon><TopRight /></el-icon> 在新标签页中打开
            </el-button>
            <el-button type="success" @click="downloadFile">
              <el-icon><Download /></el-icon> 下载
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
      class="file-info glass-descriptions"
    >
      <el-descriptions-item label="文件名称">{{ selectedFile.filename }}</el-descriptions-item>
      <el-descriptions-item label="文件类型">{{ selectedFile.type.toUpperCase() }}</el-descriptions-item>
      <el-descriptions-item label="文件大小">{{ formatFileSize(selectedFile.size) }}</el-descriptions-item>
    </el-descriptions>
  </el-card>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue';
import {
  View,
  Document,
  RefreshRight,
  Download,
  TopRight,
  ZoomIn,
  ZoomOut,
  ArrowLeft,
  ArrowRight,
} from '@element-plus/icons-vue';

// --- Props and Emits ---
const props = defineProps({
    selectedFile: {
      type: Object,
    default: null,
    },
    fileList: {
      type: Array,
    default: () => [],
  },
});

const emit = defineEmits(['select-file']);

// --- Template Refs ---
const imagePreviewContainer = ref(null);
const previewImage = ref(null);

// --- State ---
const loading = ref(false);
const loadError = ref(null);
const zoomLevel = ref(1.0);
const fileUrl = ref(null);
const isDragging = ref(false);
const startX = ref(0);
const startY = ref(0);
const scrollLeft = ref(0);
const scrollTop = ref(0);
const currentIndex = ref(-1);

// --- Computed Properties ---
const isImage = computed(() => {
  if (!props.selectedFile) return false;
  const imageTypes = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'];
  return imageTypes.includes(props.selectedFile.type.toLowerCase());
});

const isVideo = computed(() => {
  if (!props.selectedFile) return false;
  const videoTypes = ['mp4', 'webm', 'ogg', 'avi', 'mov'];
  return videoTypes.includes(props.selectedFile.type.toLowerCase());
});

const imageFiles = computed(() => {
  return props.fileList.filter(file => {
    const imageTypes = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'];
        return imageTypes.includes(file.type.toLowerCase());
      });
});

const hasPrevImage = computed(() => currentIndex.value > 0);
const hasNextImage = computed(() => currentIndex.value < imageFiles.value.length - 1);

// --- Methods ---
const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const loadFile = async (file) => {
  loading.value = true;
  loadError.value = null;
  zoomLevel.value = 1.0;

      const baseUrl = `http://localhost:5000${file.path}`;
  fileUrl.value = `${baseUrl}?t=${new Date().getTime()}`;

  if (isImage.value) {
    await nextTick();
        const img = new Image();
        img.onload = () => {
      loading.value = false;
      // 使用 requestAnimationFrame 避免 ResizeObserver 循环
      window.requestAnimationFrame(() => {
      const container = imagePreviewContainer.value;
      if (container) {
            const containerWidth = container.clientWidth;
            const containerHeight = container.clientHeight;
            const imgWidth = img.width;
            const imgHeight = img.height;

            const widthRatio = containerWidth / imgWidth;
            const heightRatio = containerHeight / imgHeight;
            const fitRatio = Math.min(widthRatio, heightRatio);

            if (fitRatio > 1.0) {
              zoomLevel.value = Math.min(fitRatio, 2.0);
            } else {
              zoomLevel.value = Math.max(fitRatio, 0.7);
            }

            container.scrollLeft = 0;
            container.scrollTop = 0;
          }
      });
        };
        img.onerror = (error) => {
      loading.value = false;
      loadError.value = 'Failed to load image. File may not exist or is corrupt.';
          console.error('Failed to load image:', error);
        };
    img.src = fileUrl.value;
      } else {
    loading.value = false;
      }
};

const retryLoad = () => {
  if (props.selectedFile) {
    loadFile(props.selectedFile);
      }
};

const handleImageError = (error) => {
  loadError.value = 'Failed to display image. The file may not exist or you may not have permission to view it.';
      console.error('Image error:', error);
};

const handleVideoError = (error) => {
  loadError.value = 'Failed to load video. The file may not exist or you may not have permission to view it.';
      console.error('Video error:', error);
};

const increaseZoom = () => {
  if (zoomLevel.value < 5) {
    zoomLevel.value = Math.min(5, parseFloat((zoomLevel.value + 0.1).toFixed(1)));
      }
};

const decreaseZoom = () => {
  if (zoomLevel.value > 0.2) {
    zoomLevel.value = Math.max(0.2, parseFloat((zoomLevel.value - 0.1).toFixed(1)));
      }
};

const resetZoom = () => {
  // 使用 requestAnimationFrame 避免 ResizeObserver 循环
  window.requestAnimationFrame(() => {
    const container = imagePreviewContainer.value;
    const imgEl = previewImage.value?.$el;

    if (isImage.value && container && imgEl?.naturalWidth) {
        const imgWidth = imgEl.naturalWidth;
        const imgHeight = imgEl.naturalHeight;

        const containerWidth = container.clientWidth;
        const containerHeight = container.clientHeight;

        const widthRatio = containerWidth / imgWidth;
        const heightRatio = containerHeight / imgHeight;

        const fitRatio = Math.min(widthRatio, heightRatio);

        if (fitRatio > 1.0) {
            zoomLevel.value = Math.min(fitRatio, 2.0);
        } else {
            zoomLevel.value = Math.max(fitRatio, 0.7);
      }

        container.scrollLeft = 0;
        container.scrollTop = 0;
    } else {
        zoomLevel.value = 1.0;
      }
  });
};

const handleWheel = (event) => {
  const container = imagePreviewContainer.value;
  if (!container) return;

      const zoomFactor = event.deltaY < 0 ? 1.1 : 0.9;
  const newZoom = parseFloat((zoomLevel.value * zoomFactor).toFixed(2));

      if (newZoom >= 0.2 && newZoom <= 5) {
    const oldZoom = zoomLevel.value;
    
    // 使用 requestAnimationFrame 避免 ResizeObserver 循环
    window.requestAnimationFrame(() => {
    zoomLevel.value = newZoom;

          const rect = container.getBoundingClientRect();
          const mouseX = event.clientX - rect.left;
          const mouseY = event.clientY - rect.top;

    const newScrollLeft = container.scrollLeft * (newZoom / oldZoom) + (mouseX * (newZoom / oldZoom) - mouseX);
    const newScrollTop = container.scrollTop * (newZoom / oldZoom) + (mouseY * (newZoom / oldZoom) - mouseY);

    container.scrollLeft = newScrollLeft;
    container.scrollTop = newScrollTop;
    });
        }
};

const openInNewTab = () => {
  if (fileUrl.value) {
    window.open(fileUrl.value, '_blank');
      }
};

const downloadFile = () => {
  if (fileUrl.value) {
        const link = document.createElement('a');
    link.href = fileUrl.value;
    link.download = props.selectedFile.filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }
};

const startDrag = (e) => {
  if (!isImage.value) return;
      e.preventDefault();
      e.stopPropagation();
  isDragging.value = true;

  const pageX = e.type === 'mousedown' ? e.pageX : e.touches[0].pageX;
  const pageY = e.type === 'mousedown' ? e.pageY : e.touches[0].pageY;
  
  startX.value = pageX;
  startY.value = pageY;

  const container = imagePreviewContainer.value;
  if(container) {
    scrollLeft.value = container.scrollLeft;
    scrollTop.value = container.scrollTop;
  }
};

const onDrag = (e) => {
  if (!isDragging.value) return;
      e.preventDefault();
      e.stopPropagation();

  const pageX = e.type === 'mousemove' ? e.pageX : e.touches[0].pageX;
  const pageY = e.type === 'mousemove' ? e.pageY : e.touches[0].pageY;
  
  const moveX = pageX - startX.value;
  const moveY = pageY - startY.value;

  const container = imagePreviewContainer.value;
  if (container) {
    container.scrollLeft = scrollLeft.value - moveX;
    container.scrollTop = scrollTop.value - moveY;
  }
};

const stopDrag = () => {
  isDragging.value = false;
};

const updateCurrentIndex = () => {
  if (!props.selectedFile || imageFiles.value.length === 0) {
    currentIndex.value = -1;
        return;
      }
  currentIndex.value = imageFiles.value.findIndex(file => file.path === props.selectedFile.path);
};

const prevImage = () => {
  if (!hasPrevImage.value) return;
  const prevFile = imageFiles.value[currentIndex.value - 1];
  emit('select-file', prevFile);
};

const nextImage = () => {
  if (!hasNextImage.value) return;
  const nextFile = imageFiles.value[currentIndex.value + 1];
  emit('select-file', nextFile);
};

// --- Watchers ---
watch(() => props.selectedFile, (newFile) => {
  if (newFile) {
    loadFile(newFile);
    updateCurrentIndex();
  } else {
    fileUrl.value = null;
    currentIndex.value = -1;
  }
  resetZoom();
}, { immediate: true });

watch(() => props.fileList, () => {
  updateCurrentIndex();
});

// --- Lifecycle Hooks ---
onMounted(() => {
  window.addEventListener('mousemove', onDrag);
  window.addEventListener('mouseup', stopDrag);
  window.addEventListener('touchmove', onDrag, { passive: false });
  window.addEventListener('touchend', stopDrag);
});

onBeforeUnmount(() => {
  window.removeEventListener('mousemove', onDrag);
  window.removeEventListener('mouseup', stopDrag);
  window.removeEventListener('touchmove', onDrag);
  window.removeEventListener('touchend', stopDrag);
});
</script>

<style scoped src="../assets/styles/filePreview.css"></style>