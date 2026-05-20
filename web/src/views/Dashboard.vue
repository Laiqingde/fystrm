<script setup lang="ts">
import { computed, onMounted, ref, h } from "vue";
import {
  NCard, NGrid, NGi, NIcon, NTag, NSpace, NEmpty, NSpin,
} from "naive-ui";
import {
  FilmOutline, FolderOpenOutline, TimeOutline, ServerOutline,
  CheckmarkCircleOutline, AlertCircleOutline, EyeOffOutline,
} from "@vicons/ionicons5";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { LineChart, BarChart } from "echarts/charts";
import { GridComponent, TooltipComponent, LegendComponent, TitleComponent } from "echarts/components";
import { getDashboardStats, type DashboardStats } from "../api";
import { isDark } from "../theme";

use([CanvasRenderer, LineChart, BarChart, GridComponent, TooltipComponent, LegendComponent, TitleComponent]);

const stats = ref<DashboardStats | null>(null);
const loading = ref(true);

async function load() {
  loading.value = true;
  try { stats.value = await getDashboardStats(); } finally { loading.value = false; }
}

onMounted(load);

function fmtSize(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 ** 2) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 ** 3) return `${(n / 1024 ** 2).toFixed(1)} MB`;
  if (n < 1024 ** 4) return `${(n / 1024 ** 3).toFixed(2)} GB`;
  return `${(n / 1024 ** 4).toFixed(2)} TB`;
}

const tiles = computed(() => {
  if (!stats.value) return [];
  const s = stats.value;
  const totalFiles = s.recent_tasks.reduce((a, t) => a + t.total_files, 0);
  return [
    { label: "媒体条目", value: s.media_count, icon: FilmOutline, color: "#5b8def", bg: "rgba(91,141,239,0.14)" },
    { label: "媒体库",   value: s.library_count, icon: FolderOpenOutline, color: "#b56bff", bg: "rgba(181,107,255,0.14)" },
    { label: "扫描任务", value: s.task_count, icon: TimeOutline, color: "#22c55e", bg: "rgba(34,197,94,0.14)" },
    { label: "总容量",   value: fmtSize(s.total_size), icon: ServerOutline, color: "#f59e0b", bg: "rgba(245,158,11,0.14)", sub: `${totalFiles} 文件` },
  ];
});

const trendOption = computed(() => {
  if (!stats.value) return {};
  const dates = stats.value.trend_7d.map(t => t.date);
  const success = stats.value.trend_7d.map(t => t.success);
  const failed = stats.value.trend_7d.map(t => t.failed);
  return {
    backgroundColor: "transparent",
    tooltip: { trigger: "axis" },
    legend: { data: ["成功", "失败"], textStyle: { color: isDark.value ? "#c9d1d9" : "#444" } },
    grid: { left: 36, right: 16, top: 32, bottom: 24 },
    xAxis: { type: "category", data: dates, axisLabel: { color: isDark.value ? "#8b949e" : "#666" } },
    yAxis: { type: "value", axisLabel: { color: isDark.value ? "#8b949e" : "#666" }, splitLine: { lineStyle: { color: isDark.value ? "rgba(255,255,255,0.06)" : "#eee" } } },
    series: [
      { name: "成功", type: "line", smooth: true, data: success, areaStyle: { opacity: 0.15 }, itemStyle: { color: "#22c55e" }, lineStyle: { color: "#22c55e" } },
      { name: "失败", type: "line", smooth: true, data: failed, areaStyle: { opacity: 0.15 }, itemStyle: { color: "#ef4444" }, lineStyle: { color: "#ef4444" } },
    ],
  };
});

const statusColor = (s: string) => ({
  done: "success", failed: "error", pending: "default", running: "info", skipped: "warning",
} as Record<string, any>)[s] || "default";

function epLabel(m: any): string | null {
  if (m.media_type === "movie") return null;
  if (m.season != null && m.episode != null) {
    return `S${String(m.season).padStart(2,"0")}E${String(m.episode).padStart(2,"0")}`;
  }
  return null;
}
</script>

<template>
  <div v-if="loading" style="display: flex; justify-content: center; padding: 60px;">
    <n-spin size="large" />
  </div>

  <div v-else-if="stats">
    <!-- 顶部 4 个 stat tile -->
    <n-grid :cols="4" :x-gap="20" :y-gap="16" responsive="screen" :item-responsive="true">
      <n-gi span="4 m:2 l:1" v-for="t in tiles" :key="t.label">
        <n-card class="fystrm-hover-lift" style="border-radius: 14px;">
          <div class="fystrm-stat">
            <div class="fystrm-stat-icon" :style="{ background: t.bg, color: t.color }">
              <n-icon :component="t.icon" />
            </div>
            <div>
              <div class="fystrm-stat-value">{{ t.value }}</div>
              <div class="fystrm-stat-label">{{ t.label }}<span v-if="(t as any).sub"> · {{ (t as any).sub }}</span></div>
            </div>
          </div>
        </n-card>
      </n-gi>
    </n-grid>

    <!-- 趋势图 + 状态分布 -->
    <n-grid :cols="3" :x-gap="20" :y-gap="20" responsive="screen" :item-responsive="true" style="margin-top: 20px;">
      <n-gi span="3 m:3 l:2">
        <n-card title="近 7 天扫描趋势" style="border-radius: 14px;">
          <div v-if="!stats.trend_7d.length" style="padding: 40px 0;">
            <n-empty description="暂无数据" />
          </div>
          <v-chart v-else :option="trendOption" style="height: 280px;" autoresize />
        </n-card>
      </n-gi>
      <n-gi span="3 m:3 l:1">
        <n-card title="刮削状态分布" style="border-radius: 14px;">
          <n-space vertical size="medium">
            <div v-for="(count, status) in stats.by_status" :key="status" style="display: flex; justify-content: space-between; align-items: center;">
              <n-tag :type="statusColor(status as string)" size="medium" round>
                <template #icon>
                  <n-icon :component="status === 'done' ? CheckmarkCircleOutline : status === 'failed' ? AlertCircleOutline : EyeOffOutline" />
                </template>
                {{ status }}
              </n-tag>
              <span style="font-size: 18px; font-weight: 600;">{{ count }}</span>
            </div>
            <div v-if="!Object.keys(stats.by_status).length">
              <n-empty description="暂无数据" />
            </div>
          </n-space>
        </n-card>
      </n-gi>
    </n-grid>

    <!-- 最近任务 + 最新媒体 -->
    <n-grid :cols="2" :x-gap="20" :y-gap="20" responsive="screen" :item-responsive="true" style="margin-top: 20px;">
      <n-gi span="2 m:2 l:1">
        <n-card title="最近扫描任务" style="border-radius: 14px;">
          <n-empty v-if="!stats.recent_tasks.length" description="暂无任务" />
          <table v-else class="fystrm-mini-table">
            <thead>
              <tr><th>#</th><th>库</th><th>状态</th><th>进度</th><th>结果</th></tr>
            </thead>
            <tbody>
              <tr v-for="t in stats.recent_tasks" :key="t.id">
                <td>#{{ t.id }}</td>
                <td>lib {{ t.library_id }}</td>
                <td><n-tag size="small" :type="statusColor(t.status)">{{ t.status }}</n-tag></td>
                <td>{{ t.processed_files }}/{{ t.total_files }}</td>
                <td>
                  <n-space :size="6">
                    <n-tag size="tiny" type="success">{{ t.success_count }}</n-tag>
                    <n-tag v-if="t.failed_count" size="tiny" type="error">{{ t.failed_count }}</n-tag>
                  </n-space>
                </td>
              </tr>
            </tbody>
          </table>
        </n-card>
      </n-gi>
      <n-gi span="2 m:2 l:1">
        <n-card title="最新媒体" style="border-radius: 14px;">
          <n-empty v-if="!stats.recent_media.length" description="暂无媒体" />
          <div v-else class="fystrm-recent-media">
            <div v-for="m in stats.recent_media" :key="m.id" class="fystrm-recent-row">
              <n-icon :component="FilmOutline" :size="16" style="opacity: 0.6;" />
              <div style="flex: 1; min-width: 0;">
                <div style="font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                  {{ m.title }}<span v-if="m.year"> ({{ m.year }})</span>
                  <span v-if="m.episode_title" style="opacity: 0.7; margin-left: 6px;">· {{ m.episode_title }}</span>
                </div>
                <div style="font-size: 12px; opacity: 0.6;">
                  {{ m.media_type }}<span v-if="epLabel(m)"> · {{ epLabel(m) }}</span><span v-if="m.tmdb_id"> · TMDB {{ m.tmdb_id }}</span>
                </div>
              </div>
              <n-tag size="small" :type="statusColor(m.scrape_status)">{{ m.scrape_status }}</n-tag>
            </div>
          </div>
        </n-card>
      </n-gi>
    </n-grid>
  </div>
</template>

<style scoped>
.fystrm-mini-table {
  width: 100%; border-collapse: collapse; font-size: 13px;
}
.fystrm-mini-table th {
  text-align: left; font-weight: 500; opacity: 0.6;
  padding: 8px 10px; border-bottom: 1px solid var(--n-border-color);
}
.fystrm-mini-table td {
  padding: 10px; border-bottom: 1px solid var(--n-border-color);
}
.fystrm-mini-table tr:last-child td { border-bottom: none; }

.fystrm-recent-media { display: flex; flex-direction: column; gap: 12px; }
.fystrm-recent-row { display: flex; align-items: center; gap: 10px; padding: 8px 0; }
</style>
