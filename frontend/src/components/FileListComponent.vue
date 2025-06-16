<template>
  <div class="file-list-component">
    <el-table :data="files" style="width: 100%">
      <el-table-column label="名称" sortable prop="name">
        <template #default="scope">
          <div v-if="scope.row.type === 'directory'" class="file-item" @click="handleItemClick(scope.row)">
            <el-icon><Folder /></el-icon>
            <span class="file-name">{{ scope.row.name }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="大小" sortable prop="size">
        <template #default="scope">
          <span v-if="scope.row.type === 'directory'">{{ formatSize(scope.row.size) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="修改日期" sortable prop="modified">
        <template #default="scope">
          <span v-if="scope.row.type === 'directory'">{{ formatDate(scope.row.modified) }}</span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script>
export default {
};
</script>

<style>
</style> 