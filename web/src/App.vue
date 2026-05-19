<script setup lang="ts">
import { computed, h, ref } from "vue";
import { RouterView, useRoute, useRouter } from "vue-router";
import {
  NConfigProvider, NMessageProvider, NLayout, NLayoutHeader, NLayoutContent,
  NIcon, NDropdown, NButton, zhCN, dateZhCN,
} from "naive-ui";
import {
  GridOutline, FilmOutline, FolderOpenOutline, TimeOutline, SettingsOutline,
  SunnyOutline, MoonOutline, EllipsisHorizontalOutline,
} from "@vicons/ionicons5";
import { naiveTheme, themeOverrides, themeMode, setThemeMode, isDark, type ThemeMode } from "./theme";

const route = useRoute();
const router = useRouter();

const menu = [
  { key: "/dashboard", label: "仪表盘", icon: GridOutline },
  { key: "/libraries", label: "媒体库", icon: FolderOpenOutline },
  { key: "/media", label: "媒体", icon: FilmOutline },
  { key: "/tasks", label: "任务", icon: TimeOutline },
  { key: "/settings", label: "设置", icon: SettingsOutline },
];

const themeOptions = [
  { label: "跟随系统", key: "auto" },
  { label: "亮色", key: "light" },
  { label: "深色", key: "dark" },
];

function onMenu(path: string) {
  router.push(path);
}

function onTheme(key: string) {
  setThemeMode(key as ThemeMode);
}
</script>

<template>
  <n-config-provider :theme="naiveTheme" :theme-overrides="themeOverrides" :locale="zhCN" :date-locale="dateZhCN">
    <n-message-provider>
      <n-layout style="min-height: 100vh;">
        <n-layout-header bordered class="fystrm-header">
          <div class="fystrm-header-inner">
            <div class="fystrm-brand">
              <span class="fystrm-logo">🎬</span>
              <span class="fystrm-logo-text">fystrm</span>
              <span class="fystrm-version">v0.2.0</span>
            </div>
            <nav class="fystrm-nav">
              <a
                v-for="m in menu"
                :key="m.key"
                class="fystrm-menu-item"
                :class="{ active: route.path.startsWith(m.key) }"
                @click="onMenu(m.key)"
              >
                <n-icon :component="m.icon" :size="18" />
                <span>{{ m.label }}</span>
              </a>
            </nav>
            <div class="fystrm-actions">
              <n-dropdown trigger="click" :options="themeOptions.map(o => ({ label: o.label, key: o.key }))" @select="onTheme">
                <n-button quaternary circle :aria-label="'主题: ' + themeMode">
                  <template #icon>
                    <n-icon :component="isDark ? MoonOutline : SunnyOutline" :size="18" />
                  </template>
                </n-button>
              </n-dropdown>
            </div>
          </div>
        </n-layout-header>
        <n-layout-content content-style="padding: 28px 32px;">
          <RouterView />
        </n-layout-content>
      </n-layout>
    </n-message-provider>
  </n-config-provider>
</template>

<style scoped>
.fystrm-header {
  position: sticky; top: 0; z-index: 10;
  backdrop-filter: blur(8px);
}
.fystrm-header-inner {
  display: flex; align-items: center; height: 60px;
  padding: 0 24px; gap: 28px;
}
.fystrm-brand { display: flex; align-items: center; gap: 10px; }
.fystrm-logo { font-size: 22px; line-height: 1; }
.fystrm-logo-text { font-size: 19px; }
.fystrm-version {
  font-size: 11px; padding: 2px 8px; border-radius: 10px;
  background: rgba(91, 141, 239, 0.12); color: #5b8def; font-weight: 600;
}

.fystrm-nav { display: flex; align-items: center; gap: 4px; flex: 1; margin-left: 16px; }
.fystrm-menu-item {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 8px 14px; border-radius: 8px;
  font-size: 14px; cursor: pointer; color: var(--ny-text-color-2);
  transition: all 0.15s ease;
}
.fystrm-menu-item:hover { background: rgba(128,128,128,0.08); }
.fystrm-menu-item.active {
  background: linear-gradient(135deg, rgba(91,141,239,0.16), rgba(181,107,255,0.10));
  color: #5b8def; font-weight: 500;
}

.fystrm-actions { display: flex; align-items: center; gap: 8px; }
</style>
