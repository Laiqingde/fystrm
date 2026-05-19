<script setup lang="ts">
import { ref, h } from "vue";
import { RouterView, useRoute, useRouter } from "vue-router";
import { NLayout, NLayoutHeader, NMenu, NConfigProvider, NMessageProvider, zhCN, dateZhCN } from "naive-ui";

const route = useRoute();
const router = useRouter();
const active = ref(route.path);

const items = [
  { label: "媒体库", key: "/libraries" },
  { label: "任务", key: "/tasks" },
  { label: "媒体", key: "/media" },
  { label: "设置", key: "/settings" },
];

function onSelect(key: string) {
  active.value = key;
  router.push(key);
}
</script>

<template>
  <n-config-provider :locale="zhCN" :date-locale="dateZhCN">
    <n-message-provider>
      <n-layout style="min-height: 100vh;">
        <n-layout-header bordered style="padding: 0 24px; display: flex; align-items: center; gap: 24px;">
          <div style="font-size: 18px; font-weight: 600;">🎬 fystrm</div>
          <n-menu mode="horizontal" :value="active" :options="items" @update:value="onSelect" style="flex: 1;" />
          <div style="opacity: 0.6; font-size: 12px;">v0.1.0</div>
        </n-layout-header>
        <n-layout content-style="padding: 24px;">
          <RouterView />
        </n-layout>
      </n-layout>
    </n-message-provider>
  </n-config-provider>
</template>
