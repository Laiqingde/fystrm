<script setup lang="ts">
import { onMounted, ref, h } from "vue";
import { NCard, NDataTable, NTag, NSelect, NSpace } from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import { listMedia, type MediaItem } from "../api";

const items = ref<MediaItem[]>([]);
const loading = ref(false);
const statusFilter = ref<string | null>(null);

async function load() {
  loading.value = true;
  try {
    items.value = await listMedia(undefined, statusFilter.value || undefined);
  } finally { loading.value = false; }
}

function fmtSize(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 ** 3) return `${(n / 1024 ** 2).toFixed(1)} MB`;
  return `${(n / 1024 ** 3).toFixed(2)} GB`;
}

const statusColor = (s: string) => ({
  done: "success", failed: "error", pending: "default", skipped: "warning",
} as Record<string, any>)[s] || "default";

const columns: DataTableColumns<MediaItem> = [
  { title: "ID", key: "id", width: 50 },
  { title: "标题", key: "title", width: 180,
    render(row) {
      if (row.media_type !== "movie" && row.episode_title) {
        return h("div", {}, [
          h("div", { style: "font-weight: 500;" }, row.title),
          h("div", { style: "font-size: 12px; opacity: 0.7;" }, row.episode_title),
        ]);
      }
      return row.title;
    },
  },
  { title: "年份", key: "year", width: 70 },
  { title: "TMDB", key: "tmdb_id", width: 90 },
  { title: "类型", key: "media_type", width: 70 },
  {
    title: "S/E",
    key: "se",
    width: 80,
    render(row) {
      if (row.season != null && row.episode != null) {
        return `S${String(row.season).padStart(2,"0")}E${String(row.episode).padStart(2,"0")}`;
      }
      return "—";
    },
  },
  { title: "大小", key: "size", width: 80, render: (row) => fmtSize(row.source_file_size) },
  {
    title: "字幕",
    key: "subs",
    width: 70,
    render(row) {
      if (!row.subtitle_paths || row.subtitle_paths.length === 0) return "—";
      return h(NTag, { type: "info", size: "small" }, { default: () => `${row.subtitle_paths!.length}` });
    },
  },
  { title: "strm", key: "strm_path", ellipsis: { tooltip: true } },
  {
    title: "状态",
    key: "scrape_status",
    width: 90,
    render: (row) => h(NTag, { type: statusColor(row.scrape_status), size: "small" }, { default: () => row.scrape_status }),
  },
];

onMounted(load);
</script>

<template>
  <n-card title="媒体条目">
    <template #header-extra>
      <n-space>
        <n-select
          v-model:value="statusFilter"
          :options="[
            { label: '全部', value: null },
            { label: 'done', value: 'done' },
            { label: 'failed', value: 'failed' },
            { label: 'skipped', value: 'skipped' },
          ]"
          style="width: 140px;"
          @update:value="load"
        />
      </n-space>
    </template>
    <n-data-table :columns="columns" :data="items" :loading="loading" :bordered="false" />
  </n-card>
</template>
