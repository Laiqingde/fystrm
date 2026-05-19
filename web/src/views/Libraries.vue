<script setup lang="ts">
import { onMounted, ref, h } from "vue";
import {
  NCard, NDataTable, NButton, NSpace, NModal, NForm, NFormItem, NInput, NSelect,
  NTag, NPopconfirm, useMessage
} from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import { listLibraries, createLibrary, deleteLibrary, startScan, type Library } from "../api";

const message = useMessage();
const libs = ref<Library[]>([]);
const loading = ref(false);
const showCreate = ref(false);
const form = ref({
  name: "",
  source_path: "",
  target_strm_path: "",
  cd2_mount_prefix: "",
  media_type: "movie",
  enabled: true,
});

async function load() {
  loading.value = true;
  try { libs.value = await listLibraries(); } finally { loading.value = false; }
}

async function submit() {
  if (!form.value.name || !form.value.source_path || !form.value.target_strm_path) {
    message.warning("请填完必填项");
    return;
  }
  try {
    await createLibrary(form.value);
    message.success("创建成功");
    showCreate.value = false;
    form.value = { name: "", source_path: "", target_strm_path: "", cd2_mount_prefix: "", media_type: "movie", enabled: true };
    await load();
  } catch (e: any) {
    message.error("创建失败: " + (e?.response?.data?.detail || e.message));
  }
}

async function onScan(lib: Library) {
  try {
    const task = await startScan(lib.id);
    message.success(`扫描已入队 task #${task.id}`);
  } catch (e: any) {
    message.error("扫描启动失败: " + (e?.response?.data?.detail || e.message));
  }
}

async function onDelete(lib: Library) {
  await deleteLibrary(lib.id);
  message.success("删除成功");
  await load();
}

const columns: DataTableColumns<Library> = [
  { title: "ID", key: "id", width: 60 },
  { title: "名称", key: "name", width: 160 },
  { title: "扫描源", key: "source_path", ellipsis: { tooltip: true } },
  { title: "strm 输出", key: "target_strm_path", ellipsis: { tooltip: true } },
  { title: "CD2 前缀", key: "cd2_mount_prefix", ellipsis: { tooltip: true } },
  {
    title: "类型",
    key: "media_type",
    width: 80,
    render: (row) => h(NTag, { type: "info", size: "small" }, { default: () => row.media_type }),
  },
  {
    title: "操作",
    key: "actions",
    width: 200,
    render(row) {
      return h(NSpace, {}, () => [
        h(NButton, { size: "small", type: "primary", onClick: () => onScan(row) }, { default: () => "扫描" }),
        h(NPopconfirm, { onPositiveClick: () => onDelete(row) }, {
          default: () => "确认删除?",
          trigger: () => h(NButton, { size: "small", type: "error" }, { default: () => "删除" }),
        }),
      ]);
    },
  },
];

onMounted(load);
</script>

<template>
  <n-card title="媒体库">
    <template #header-extra>
      <n-button type="primary" @click="showCreate = true">+ 新建</n-button>
    </template>
    <n-data-table :columns="columns" :data="libs" :loading="loading" :bordered="false" />
  </n-card>

  <n-modal v-model:show="showCreate" preset="card" title="新建媒体库" style="width: 600px;">
    <n-form>
      <n-form-item label="名称 *">
        <n-input v-model:value="form.name" placeholder="例: 我的电影库" />
      </n-form-item>
      <n-form-item label="扫描源路径 *" :feedback="'容器内的路径，例 /scan-source/Movies'">
        <n-input v-model:value="form.source_path" placeholder="/scan-source/Movies" />
      </n-form-item>
      <n-form-item label="strm 输出路径 *" :feedback="'容器内的路径，例 /media/电影'">
        <n-input v-model:value="form.target_strm_path" placeholder="/media/电影" />
      </n-form-item>
      <n-form-item label="CD2 路径前缀 *" :feedback="'写进 .strm 文件的前缀，Emby 通过这个路径回源'">
        <n-input v-model:value="form.cd2_mount_prefix" placeholder="/CloudNAS/115/电影" />
      </n-form-item>
      <n-form-item label="类型">
        <n-select v-model:value="form.media_type" :options="[
          { label: '电影', value: 'movie' },
          { label: '剧集', value: 'tv' },
          { label: '混合', value: 'mixed' },
        ]" />
      </n-form-item>
      <n-button type="primary" @click="submit" block>创建</n-button>
    </n-form>
  </n-modal>
</template>
