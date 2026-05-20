<script setup lang="ts">
import { computed, h, onMounted, onUnmounted, ref } from "vue";
import {
  NCard, NSpace, NButton, NTag, NIcon, NSelect, NSwitch, NEmpty,
} from "naive-ui";
import {
  PauseOutline, PlayOutline, TrashOutline, ArrowDownOutline, RefreshOutline,
  FilmOutline, SyncOutline, SearchOutline, ImageOutline, NotificationsOutline,
  CloudOutline, TerminalOutline,
} from "@vicons/ionicons5";
import { api } from "../api";

interface LogLine {
  ts: string;
  level: string;
  module: string;
  function: string;
  line: number;
  msg: string;
  category: string;
}

const logs = ref<LogLine[]>([]);
const MAX = 2000;
const paused = ref(false);
const autoScroll = ref(true);
const categoryFilter = ref<string | null>(null);
const levelFilter = ref<string | null>(null);
const logContainer = ref<HTMLElement | null>(null);
let ws: WebSocket | null = null;

const categories = [
  { label: "全部", value: null },
  { label: "strm 生成", value: "strm" },
  { label: "刮削", value: "scrape" },
  { label: "元数据", value: "metadata" },
  { label: "扫描", value: "scan" },
  { label: "Webhook", value: "webhook" },
  { label: "Emby", value: "emby" },
  { label: "其他", value: "general" },
];

const levels = [
  { label: "全部级别", value: null },
  { label: "DEBUG", value: "DEBUG" },
  { label: "INFO", value: "INFO" },
  { label: "WARNING", value: "WARNING" },
  { label: "ERROR", value: "ERROR" },
];

const categoryColor = (c: string): string => ({
  strm: "#5b8def",
  scrape: "#b56bff",
  metadata: "#f59e0b",
  scan: "#22c55e",
  webhook: "#06b6d4",
  emby: "#ef4444",
  general: "#9ca3af",
} as Record<string, string>)[c] || "#9ca3af";

const categoryIcon = (c: string) => ({
  strm: FilmOutline,
  scrape: SearchOutline,
  metadata: ImageOutline,
  scan: SyncOutline,
  webhook: NotificationsOutline,
  emby: CloudOutline,
} as Record<string, any>)[c] || TerminalOutline;

const levelColor = (lv: string) => ({
  DEBUG: "#9ca3af",
  INFO: "#5b8def",
  WARNING: "#f59e0b",
  ERROR: "#ef4444",
  CRITICAL: "#dc2626",
} as Record<string, string>)[lv] || "#9ca3af";

const filteredLogs = computed(() => {
  return logs.value.filter(l => {
    if (categoryFilter.value && l.category !== categoryFilter.value) return false;
    if (levelFilter.value && l.level !== levelFilter.value) return false;
    return true;
  });
});

function appendLog(line: LogLine) {
  if (paused.value) return;
  logs.value.push(line);
  if (logs.value.length > MAX) logs.value.splice(0, logs.value.length - MAX);
  if (autoScroll.value) {
    requestAnimationFrame(() => {
      const el = logContainer.value;
      if (el) el.scrollTop = el.scrollHeight;
    });
  }
}

async function loadHistory() {
  try {
    const r = await api.get<LogLine[]>("/api/logs/recent?limit=200");
    // 历史是倒序 (新在前), 我们要正序 (老在前, 新在底)
    logs.value = r.data.reverse();
    requestAnimationFrame(() => {
      const el = logContainer.value;
      if (el) el.scrollTop = el.scrollHeight;
    });
  } catch (e) {
    console.error("load history failed", e);
  }
}

function connect() {
  if (ws) { ws.close(); ws = null; }
  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}/ws/logs`);
  ws.onmessage = (e) => {
    try {
      const obj = JSON.parse(e.data) as LogLine;
      appendLog(obj);
    } catch {}
  };
  ws.onclose = () => { setTimeout(connect, 2000); };
}

function clearLogs() { logs.value = []; }

function scrollToBottom() {
  const el = logContainer.value;
  if (el) el.scrollTop = el.scrollHeight;
}

function fmtTime(ts: string) {
  return ts.replace("T", " ").replace(/\.\d+Z$/, "").substring(0, 19);
}

function shortModule(m: string) {
  const parts = m.split(".");
  if (parts.length <= 2) return m;
  return parts.slice(-2).join(".");
}

onMounted(async () => {
  await loadHistory();
  connect();
});

onUnmounted(() => {
  if (ws) { ws.close(); ws = null; }
});
</script>

<template>
  <n-card title="实时日志" style="border-radius: 14px;">
    <template #header-extra>
      <n-space :size="8">
        <n-select v-model:value="categoryFilter" :options="categories" size="small" style="width: 130px;" />
        <n-select v-model:value="levelFilter" :options="levels" size="small" style="width: 120px;" />
        <n-button size="small" quaternary @click="paused = !paused" :type="paused ? 'warning' : 'default'">
          <template #icon><n-icon :component="paused ? PlayOutline : PauseOutline" /></template>
          {{ paused ? "继续" : "暂停" }}
        </n-button>
        <n-button size="small" quaternary @click="clearLogs">
          <template #icon><n-icon :component="TrashOutline" /></template>
          清空
        </n-button>
        <n-button size="small" quaternary @click="scrollToBottom">
          <template #icon><n-icon :component="ArrowDownOutline" /></template>
        </n-button>
        <n-button size="small" quaternary @click="loadHistory">
          <template #icon><n-icon :component="RefreshOutline" /></template>
        </n-button>
      </n-space>
    </template>

    <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 12px; font-size: 13px;">
      <span style="opacity: 0.6;">自动滚动</span>
      <n-switch v-model:value="autoScroll" size="small" />
      <span style="opacity: 0.6;">共 {{ filteredLogs.length }} 条 / 缓冲 {{ logs.length }}</span>
      <n-tag v-if="paused" type="warning" size="small" round>已暂停</n-tag>
    </div>

    <n-empty v-if="!filteredLogs.length" description="暂无日志" />

    <div v-else ref="logContainer" class="fystrm-log-pane">
      <div v-for="(l, i) in filteredLogs" :key="i" class="fystrm-log-line">
        <span class="fystrm-log-ts">{{ fmtTime(l.ts) }}</span>
        <span class="fystrm-log-level" :style="{ color: levelColor(l.level) }">{{ l.level.padEnd(7) }}</span>
        <span class="fystrm-log-cat" :style="{ color: categoryColor(l.category), borderColor: categoryColor(l.category) }">
          <n-icon :component="categoryIcon(l.category)" :size="11" /> {{ l.category }}
        </span>
        <span class="fystrm-log-mod">{{ shortModule(l.module) }}:{{ l.line }}</span>
        <span class="fystrm-log-msg">{{ l.msg }}</span>
      </div>
    </div>
  </n-card>
</template>

<style scoped>
.fystrm-log-pane {
  height: calc(100vh - 280px);
  min-height: 400px;
  overflow-y: auto;
  background: rgba(0,0,0,0.04);
  border-radius: 8px;
  padding: 12px;
  font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  font-size: 12.5px;
  line-height: 1.6;
}
:global(html.dark) .fystrm-log-pane {
  background: rgba(0,0,0,0.3);
}

.fystrm-log-line {
  display: grid;
  grid-template-columns: 140px 60px 100px 180px 1fr;
  gap: 10px;
  white-space: nowrap;
  padding: 2px 0;
}
.fystrm-log-ts { opacity: 0.5; }
.fystrm-log-level { font-weight: 600; }
.fystrm-log-cat {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 0 6px; border-radius: 10px;
  border: 1px solid; font-size: 11px;
  background: rgba(255,255,255,0.02);
}
.fystrm-log-mod { opacity: 0.55; }
.fystrm-log-msg {
  white-space: pre-wrap; word-break: break-all;
  overflow: hidden; text-overflow: ellipsis;
}
.fystrm-log-line:hover { background: rgba(91,141,239,0.08); }
</style>
