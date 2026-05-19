<script setup lang="ts">
import { onMounted, onUnmounted, ref, h, computed } from "vue";
import { NCard, NDataTable, NTag, NProgress, NButton, NSpace, NLog } from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import { listTasks, type ScanTask } from "../api";

const tasks = ref<ScanTask[]>([]);
const loading = ref(false);
const wsLogs = ref<string[]>([]);
const liveTaskId = ref<number | null>(null);
let pollTimer: number | null = null;
let ws: WebSocket | null = null;

async function load() {
  loading.value = true;
  try { tasks.value = await listTasks(50); } finally { loading.value = false; }
}

function startPoll() {
  if (pollTimer !== null) return;
  pollTimer = window.setInterval(load, 3000);
}
function stopPoll() {
  if (pollTimer !== null) { clearInterval(pollTimer); pollTimer = null; }
}

function watch(task: ScanTask) {
  if (ws) { ws.close(); ws = null; }
  wsLogs.value = [];
  liveTaskId.value = task.id;
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const url = `${proto}://${location.host}/ws/tasks/${task.id}`;
  ws = new WebSocket(url);
  ws.onmessage = (e) => {
    wsLogs.value.unshift(e.data);
    if (wsLogs.value.length > 200) wsLogs.value.pop();
    if (e.data.includes('"event": "done"') || e.data.includes('"event":"done"')) {
      load();
    }
  };
  ws.onerror = () => wsLogs.value.unshift("[error] WebSocket connection error");
}

function stopWatch() {
  if (ws) { ws.close(); ws = null; }
  liveTaskId.value = null;
  wsLogs.value = [];
}

const wsText = computed(() => wsLogs.value.join("\n"));

const statusColor = (s: string) => ({
  pending: "default", running: "info", done: "success", failed: "error",
} as Record<string, any>)[s] || "default";

const columns: DataTableColumns<ScanTask> = [
  { title: "ID", key: "id", width: 60 },
  { title: "库", key: "library_id", width: 60 },
  {
    title: "状态",
    key: "status",
    width: 100,
    render: (row) => h(NTag, { type: statusColor(row.status) }, { default: () => row.status }),
  },
  {
    title: "进度",
    key: "progress",
    width: 220,
    render(row) {
      const pct = row.total_files > 0 ? Math.round((row.processed_files / row.total_files) * 100) : 0;
      return h(NProgress, { type: "line", percentage: pct, "indicator-placement": "inside" }, { default: () => `${row.processed_files}/${row.total_files}` });
    },
  },
  { title: "成功", key: "success_count", width: 60 },
  { title: "失败", key: "failed_count", width: 60 },
  { title: "开始时间", key: "started_at", width: 180 },
  { title: "结束时间", key: "finished_at", width: 180 },
  {
    title: "操作",
    key: "actions",
    width: 100,
    render(row) {
      return h(NButton, { size: "small", onClick: () => watch(row) }, { default: () => "实时" });
    },
  },
];

onMounted(() => { load(); startPoll(); });
onUnmounted(() => { stopPoll(); if (ws) ws.close(); });
</script>

<template>
  <n-card title="扫描任务">
    <template #header-extra>
      <n-space>
        <span style="opacity: 0.6;">每 3s 自动刷新</span>
        <n-button size="small" @click="load">立即刷新</n-button>
      </n-space>
    </template>
    <n-data-table :columns="columns" :data="tasks" :loading="loading" :bordered="false" />
  </n-card>

  <n-card v-if="liveTaskId !== null" :title="`实时进度 — Task #${liveTaskId}`" style="margin-top: 16px;">
    <template #header-extra>
      <n-button size="small" @click="stopWatch">关闭</n-button>
    </template>
    <n-log :rows="15" :log="wsText" trim />
  </n-card>
</template>
