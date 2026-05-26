<script setup lang="ts">
import { onMounted, onUnmounted, ref, h, computed } from "vue";
import {
  NCard, NDataTable, NTag, NProgress, NButton, NSpace, NLog, NIcon,
} from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import {
  EyeOutline, RefreshOutline, PulseOutline, CloseOutline,
  CheckmarkCircleOutline, AlertCircleOutline, TimeOutline, PlayCircleOutline,
} from "@vicons/ionicons5";
import { listTasks, getToken, fmtDateTime, type ScanTask } from "../api";

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
  const url = `${proto}://${location.host}/ws/tasks/${task.id}?token=${encodeURIComponent(getToken() || "")}`;
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

const statusIcon = (s: string) => ({
  pending: TimeOutline, running: PlayCircleOutline, done: CheckmarkCircleOutline, failed: AlertCircleOutline,
} as Record<string, any>)[s] || TimeOutline;

const columns: DataTableColumns<ScanTask> = [
  { title: "ID", key: "id", width: 60, render: (r) => h("span", {}, `#${r.id}`) },
  { title: "库", key: "library_id", width: 60, render: (r) => h("span", { style: "opacity: 0.7;" }, `lib ${r.library_id}`) },
  {
    title: "状态", key: "status", width: 100,
    render(row) {
      return h(NTag, { type: statusColor(row.status), size: "medium", round: true }, {
        icon: () => h(NIcon, { component: statusIcon(row.status) }),
        default: () => row.status,
      });
    },
  },
  {
    title: "进度", key: "progress", width: 280,
    render(row) {
      const pct = row.total_files > 0 ? Math.round((row.processed_files / row.total_files) * 100) : 0;
      // stage 文字优先 (discovering/syncing_metadata 时显示)
      if (row.status === "running" && row.stage && row.stage !== "processing" && row.stage !== "done") {
        return h("div", { style: "display: flex; flex-direction: column; gap: 4px;" }, [
          h(NProgress, {
            type: "line", percentage: pct, "indicator-placement": "inside",
            height: 18, borderRadius: 9, status: "info",
            processing: true,
          }, { default: () => row.stage }),
          h("div", { style: "font-size: 11px; opacity: 0.65;" }, row.stage_message || ""),
        ]);
      }
      return h(NProgress, {
        type: "line", percentage: pct, "indicator-placement": "inside",
        height: 18, borderRadius: 9, status: row.status === "failed" ? "error" : pct === 100 ? "success" : "info",
      }, { default: () => `${row.processed_files}/${row.total_files}` });
    },
  },
  {
    title: "结果", key: "_result", width: 100,
    render(row) {
      return h(NSpace, { size: 6 }, () => [
        h(NTag, { size: "small", type: "success", round: true }, { default: () => row.success_count }),
        row.failed_count > 0 ? h(NTag, { size: "small", type: "error", round: true }, { default: () => row.failed_count }) : null,
      ]);
    },
  },
  { title: "开始", key: "started_at", width: 170, render: (r) => fmtDateTime(r.started_at) },
  { title: "结束", key: "finished_at", width: 170, render: (r) => fmtDateTime(r.finished_at) },
  {
    title: "操作", key: "actions", width: 100,
    render(row) {
      return h(NButton, { size: "small", quaternary: true, type: "primary", onClick: () => watch(row) }, {
        icon: () => h(NIcon, { component: EyeOutline }),
        default: () => "实时",
      });
    },
  },
];

onMounted(() => { load(); startPoll(); });
onUnmounted(() => { stopPoll(); if (ws) ws.close(); });
</script>

<template>
  <n-card title="扫描任务" style="border-radius: 14px;">
    <template #header-extra>
      <n-space>
        <span style="opacity: 0.55; font-size: 13px;">
          <n-icon :component="PulseOutline" :size="14" style="vertical-align: -2px; margin-right: 4px;" />
          每 3s 自动刷新
        </span>
        <n-button size="small" quaternary @click="load">
          <template #icon><n-icon :component="RefreshOutline" /></template>
          立即刷新
        </n-button>
      </n-space>
    </template>
    <n-data-table :columns="columns" :data="tasks" :loading="loading" :bordered="false" />
  </n-card>

  <n-card v-if="liveTaskId !== null" :title="`实时进度 — Task #${liveTaskId}`" style="margin-top: 20px; border-radius: 14px;">
    <template #header-extra>
      <n-button size="small" quaternary @click="stopWatch">
        <template #icon><n-icon :component="CloseOutline" /></template>
        关闭
      </n-button>
    </template>
    <n-log :rows="15" :log="wsText" trim />
  </n-card>
</template>
