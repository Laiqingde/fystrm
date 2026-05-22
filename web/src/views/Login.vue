<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import {
  NCard, NForm, NFormItem, NInput, NButton, NIcon, useMessage,
} from "naive-ui";
import { PersonOutline, LockClosedOutline, LogInOutline } from "@vicons/ionicons5";
import { login, setToken, setStoredUser } from "../api";

const router = useRouter();
const message = useMessage();
const username = ref("admin");
const password = ref("");
const loading = ref(false);

async function submit() {
  if (!username.value || !password.value) {
    message.warning("请输入用户名和密码"); return;
  }
  loading.value = true;
  try {
    const r = await login(username.value, password.value);
    setToken(r.access_token);
    setStoredUser(r.user);
    message.success(`欢迎 ${r.user.username}`);
    const redirect = (router.currentRoute.value.query.redirect as string) || "/dashboard";
    router.replace(redirect);
  } catch (e: any) {
    message.error(e?.response?.data?.detail || e.message || "登录失败");
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="fystrm-login-bg">
    <n-card class="fystrm-login-card" :bordered="false">
      <div class="fystrm-login-brand">
        <span class="fystrm-login-logo">🎬</span>
        <span class="fystrm-login-title">fystrm</span>
      </div>
      <p class="fystrm-login-sub">媒体库管理中枢 · 登录</p>
      <n-form @submit.prevent="submit">
        <n-form-item label="用户名">
          <n-input v-model:value="username" placeholder="admin" :input-props="{ autocomplete: 'username' }">
            <template #prefix><n-icon :component="PersonOutline" /></template>
          </n-input>
        </n-form-item>
        <n-form-item label="密码">
          <n-input v-model:value="password" type="password" show-password-on="click" placeholder="••••••••"
            :input-props="{ autocomplete: 'current-password' }" @keyup.enter="submit">
            <template #prefix><n-icon :component="LockClosedOutline" /></template>
          </n-input>
        </n-form-item>
        <n-button type="primary" block size="large" :loading="loading" @click="submit">
          <template #icon><n-icon :component="LogInOutline" /></template>
          登录
        </n-button>
      </n-form>
      <p class="fystrm-login-hint">首次登录? 默认管理员密码在服务器启动日志</p>
    </n-card>
  </div>
</template>

<style scoped>
.fystrm-login-bg {
  min-height: 100vh;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #5b8def 0%, #b56bff 100%);
  padding: 20px;
}
.fystrm-login-card {
  width: 100%; max-width: 400px;
  padding: 32px;
  border-radius: 18px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.2);
}
.fystrm-login-brand {
  display: flex; align-items: center; justify-content: center; gap: 12px;
  margin-bottom: 8px;
}
.fystrm-login-logo { font-size: 36px; }
.fystrm-login-title {
  font-size: 28px; font-weight: 700;
  background: linear-gradient(135deg, #5b8def, #b56bff);
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
.fystrm-login-sub {
  text-align: center; font-size: 13px; opacity: 0.6;
  margin: 0 0 28px;
}
.fystrm-login-hint {
  font-size: 12px; opacity: 0.5; text-align: center;
  margin: 18px 0 0;
}
</style>
