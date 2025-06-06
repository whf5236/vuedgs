<template>
  <div class="profile-container">
    <el-card class="profile-card">
      <template #header>
        <div class="card-header">
          <h2>个人信息设置</h2>
        </div>
      </template>

      <el-form 
        ref="profileForm" 
        :model="form" 
        :rules="rules" 
        label-width="100px"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" disabled></el-input>
        </el-form-item>

        <el-form-item label="昵称" prop="nickname">
          <el-input v-model="form.nickname" placeholder="请输入昵称"></el-input>
        </el-form-item>

        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱"></el-input>
        </el-form-item>

        <el-divider>修改密码</el-divider>

        <el-form-item label="当前密码" prop="currentPassword">
          <el-input 
            v-model="form.currentPassword" 
            type="password" 
            placeholder="请输入当前密码"
            show-password
          ></el-input>
        </el-form-item>

        <el-form-item label="新密码" prop="newPassword">
          <el-input 
            v-model="form.newPassword" 
            type="password" 
            placeholder="请输入新密码"
            show-password
          ></el-input>
        </el-form-item>

        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input 
            v-model="form.confirmPassword" 
            type="password" 
            placeholder="请确认新密码"
            show-password
          ></el-input>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="submitForm">保存修改</el-button>
          <el-button @click="resetForm">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script>
import axios from 'axios'
import { ElMessage } from 'element-plus'

export default {
  name: 'Profile',
  data() {
    const validatePass = (rule, value, callback) => {
      if (value === '') {
        callback(new Error('请输入密码'))
      } else {
        if (this.form.confirmPassword !== '') {
          this.$refs.profileForm.validateField('confirmPassword')
        }
        callback()
      }
    }
    const validatePass2 = (rule, value, callback) => {
      if (value === '') {
        callback(new Error('请再次输入密码'))
      } else if (value !== this.form.newPassword) {
        callback(new Error('两次输入密码不一致!'))
      } else {
        callback()
      }
    }

    return {
      form: {
        username: '',
        nickname: '',
        email: '',
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
      },
      rules: {
        email: [
          { required: true, message: '请输入邮箱地址', trigger: 'blur' },
          { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
        ],
        nickname: [
          { required: true, message: '请输入昵称', trigger: 'blur' },
          { min: 2, max: 20, message: '长度在 2 到 20 个字符', trigger: 'blur' }
        ],
        newPassword: [{ validator: validatePass, trigger: 'blur' }],
        confirmPassword: [{ validator: validatePass2, trigger: 'blur' }]
      }
    }
  },
  mounted() {
    this.loadUserInfo()
  },
  methods: {
    async loadUserInfo() {
      try {
        const response = await axios.get('/api/user/profile')
        const { username, nickname, email } = response.data
        this.form.username = username
        this.form.nickname = nickname
        this.form.email = email
      } catch (error) {
        ElMessage.error('获取用户信息失败')
      }
    },
    async submitForm() {
      try {
        await this.$refs.profileForm.validate()
        const response = await axios.post('/api/user/profile/update', this.form)
        if (response.data.success) {
          ElMessage.success('个人信息更新成功')
          this.resetPasswords()
        }
      } catch (error) {
        ElMessage.error(error.response?.data?.message || '更新失败')
      }
    },
    resetForm() {
      this.$refs.profileForm.resetFields()
    },
    resetPasswords() {
      this.form.currentPassword = ''
      this.form.newPassword = ''
      this.form.confirmPassword = ''
    }
  }
}
</script>

<style scoped>
.profile-container {
  max-width: 800px;
  margin: 20px auto;
  padding: 0 20px;
}

.profile-card {
  margin-top: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.el-divider {
  margin: 24px 0;
}
</style>
