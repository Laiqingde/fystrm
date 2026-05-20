<script setup lang="ts">
import { onMounted, ref, h, computed } from "vue";
import {
  NCard, NDataTable, NTag, NSelect, NSpace, NIcon, NEmpty, NRadioGroup, NRadioButton, NImage,
} from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import { GridOutline, ListOutline, FilmOutline, TvOutline, ImageOutline } from "@vicons/ionicons5";
import { listMedia, type MediaItem } from "../api";

const items = ref<MediaItem[]>([]);
const loading = ref(false);
const statusFilter = ref<string | null>(null);
const viewMode = ref<"table" | "grid">("table");

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

function posterUrl(m: MediaItem): string | null {
  // poster_path 是容器内绝对路径如 /media/.../poster.jpg
  // 我们通过后端代理（暂时不接，先用 fallback）；这里 placeholder
  return null;
}

function seLabel(m: MediaItem): string | null {
  if (m.season != null && m.episode != null) {
    return `S${String(m.season).padStart(2,"0")}E${String(m.episode).padStart(2,"0")}`;
  }
  return null;
}

const columns: DataTableColumns<MediaItem> = [
  { title: "ID", key: "id", width: 50 },
  {
    title: "标题", key: "title", minWidth: 200,
    render(row) {
      const children = [
        h("div", { style: "display: flex; align-items: center; gap: 8px;" }, [
          h(NIcon, { component: row.media_type === "tv" || row.media_type === "anime" ? TvOutline : FilmOutline, size: 16, color: "#5b8def" }),
          h("span", { style: "font-weight: 500;" }, row.title),
        ]),
      ];
      if (row.episode_title) {
        children.push(h("div", { style: "font-size: 12px; opacity: 0.6; margin-left: 24px;" }, row.episode_title));
      }
      return h("div", {}, children);
    },
  },
  { title: "年份", key: "year", width: 70 },
  { title: "TMDB", key: "tmdb_id", width: 90 },
  {
    title: "类型", key: "media_type", width: 80,
    render: (r) => h(NTag, { size: "small", round: true }, { default: () => r.media_type }),
  },
  {
    title: "S/E", key: "se", width: 90,
    render: (r) => seLabel(r) ? h(NTag, { size: "small", type: "info", round: true, bordered: false }, { default: () => seLabel(r) }) : "—",
  },
  { title: "大小", key: "size", width: 90, render: (r) => fmtSize(r.source_file_size) },
  {
    title: "字幕", key: "subs", width: 70,
    render(r) {
      if (!r.subtitle_paths || r.subtitle_paths.length === 0) return "—";
      return h(NTag, { type: "info", size: "small", round: true, bordered: false }, { default: () => r.subtitle_paths!.length });
    },
  },
  { title: "strm", key: "strm_path", ellipsis: { tooltip: true } },
  {
    title: "状态", key: "scrape_status", width: 100,
    render: (r) => h(NTag, { type: statusColor(r.scrape_status), size: "small", round: true }, { default: () => r.scrape_status }),
  },
];

onMounted(load);
</script>

<template>
  <n-card title="媒体条目" style="border-radius: 14px;">
    <template #header-extra>
      <n-space>
        <n-select
          v-model:value="statusFilter"
          :options="[
            { label: '全部状态', value: null },
            { label: 'done', value: 'done' },
            { label: 'failed', value: 'failed' },
            { label: 'skipped', value: 'skipped' },
          ]"
          style="width: 140px;"
          @update:value="load"
        />
        <n-radio-group v-model:value="viewMode" size="small">
          <n-radio-button value="table">
            <n-icon :component="ListOutline" />
          </n-radio-button>
          <n-radio-button value="grid">
            <n-icon :component="GridOutline" />
          </n-radio-button>
        </n-radio-group>
      </n-space>
    </template>

    <n-data-table v-if="viewMode === 'table'" :columns="columns" :data="items" :loading="loading" :bordered="false" />

    <div v-else-if="viewMode === 'grid'" class="fystrm-media-grid">
      <n-empty v-if="!items.length" description="暂无媒体" />
      <div v-for="m in items" :key="m.id" class="fystrm-media-card">
        <div class="fystrm-poster-wrap">
          <n-icon :component="ImageOutline" :size="36" style="opacity: 0.3;" />
        </div>
        <div class="fystrm-media-meta">
          <div class="fystrm-media-title">{{ m.title }}<span v-if="m.year" style="opacity: 0.6;"> ({{ m.year }})</span></div>
          <div v-if="m.episode_title" class="fystrm-media-sub">{{ m.episode_title }}</div>
          <n-space size="6" :wrap="false" style="margin-top: 6px;">
            <n-tag size="tiny" round bordered>{{ m.media_type }}</n-tag>
            <n-tag v-if="seLabel(m)" size="tiny" type="info" round :bordered="false">{{ seLabel(m) }}</n-tag>
            <n-tag size="tiny" round bordered>{{ fmtSize(m.source_file_size) }}</n-tag>
            <n-tag v-if="m.subtitle_paths?.length" size="tiny" type="info" round :bordered="false">字幕 {{ m.subtitle_paths.length }}</n-tag>
          </n-space>
          <n-tag :type="statusColor(m.scrape_status)" size="tiny" round style="margin-top: 8px;">{{ m.scrape_status }}</n-tag>
        </div>
      </div>
    </div>
  </n-card>
</template>

<style scoped>
.fystrm-media-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}
.fystrm-media-card {
  border: 1px solid var(--n-border-color);
  border-radius: 12px;
  overflow: hidden;
  background: var(--n-card-color);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.fystrm-media-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--fystrm-shadow-strong);
}
.fystrm-poster-wrap {
  aspect-ratio: 2 / 3;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, rgba(91,141,239,0.08), rgba(181,107,255,0.06));
}
.fystrm-media-meta { padding: 10px 12px; }
.fystrm-media-title { font-weight: 600; font-size: 14px; line-height: 1.3; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fystrm-media-sub { font-size: 12px; opacity: 0.65; margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
