<script setup lang="ts">
import { onMounted, ref } from "vue";
import { NCard, NDescriptions, NDescriptionsItem, NTag, NAlert, NButton } from "naive-ui";
import { getSettings, type Settings } from "../api";

const s = ref<Settings | null>(null);

async function load() {
  s.value = await getSettings();
}
onMounted(load);
</script>

<template>
  <n-card title="设置">
    <n-alert type="info" style="margin-bottom: 16px;">
      v0.1 设置只读，编辑请改服务器 <code>/opt/fystrm/.env</code> 后重启容器。
    </n-alert>
    <n-descriptions v-if="s" :column="2" bordered>
      <n-descriptions-item label="TMDB 已配置">
        <n-tag :type="s.tmdb_configured ? 'success' : 'error'">{{ s.tmdb_configured ? '是' : '否' }}</n-tag>
      </n-descriptions-item>
      <n-descriptions-item label="TMDB 语言">{{ s.tmdb_language }}</n-descriptions-item>
      <n-descriptions-item label="Emby 已配置">
        <n-tag :type="s.emby_configured ? 'success' : 'warning'">{{ s.emby_configured ? '是' : '未配置（不影响扫描+strm 生成）' }}</n-tag>
      </n-descriptions-item>
      <n-descriptions-item label="Emby URL">{{ s.emby_url || '—' }}</n-descriptions-item>
      <n-descriptions-item label="日志级别">{{ s.log_level }}</n-descriptions-item>
      <n-descriptions-item label="调试模式">
        <n-tag :type="s.debug ? 'warning' : 'default'">{{ s.debug }}</n-tag>
      </n-descriptions-item>
    </n-descriptions>
    <div style="margin-top: 16px;">
      <n-button @click="load">刷新</n-button>
    </div>
  </n-card>
</template>
