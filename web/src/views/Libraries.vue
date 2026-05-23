<script setup lang="ts">
import { onMounted, ref, h, computed, watch } from "vue";
import {
  NCard, NDataTable, NButton, NSpace, NModal, NForm, NFormItem, NInput, NSelect,
  NTag, NPopconfirm, NIcon, NTooltip, NCheckbox, NSwitch, useMessage,
} from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import {
  AddOutline, PlayOutline, TrashOutline, FolderOpenOutline, CloudOutline,
  TvOutline, FilmOutline, AlbumsOutline, EllipseSharp,
  CreateOutline, SaveOutline,
} from "@vicons/ionicons5";
import { listLibraries, createLibrary, updateLibrary, deleteLibrary, startScan, type Library } from "../api";

const message = useMessage();
const libs = ref<Library[]>([]);
const loading = ref(false);
const showCreate = ref(false);

const defaultForm = () => ({
  name: "", source_path: "", target_strm_path: "", cd2_mount_prefix: "",
  media_type: "mixed", enabled: true,
  strm_mode: "cd2_local", webdav_base_url: "", webdav_path_prefix: "",
  strm_extensions: ".mp4;.mkv;.ts;.iso;.rmvb;.avi;.mov;.mpeg;.mpg;.wmv;.3gp;.asf;.m4v;.flv;.m2ts;.tp;.f4v",
  metadata_extensions: ".nfo;.jpg;.png",
  scrape_enabled: true,
  same_as_source: true,
});
const editingLib = ref<Library | null>(null);
const isEditing = computed(() => editingLib.value !== null);
const form = ref(defaultForm());
const cloneFromId = ref<number | null>(null);

const cloneOptions = computed(() => libs.value.map(l => ({
  label: `${l.name}  (#${l.id} · ${l.source_path})`,
  value: l.id,
})));

function copyFromLib(libId: number | null) {
  if (libId == null) return;
  const src = libs.value.find(l => l.id === libId);
  if (!src) return;
  form.value = {
    name: "",  // 名字留空, 用户自己填
    source_path: src.source_path,
    target_strm_path: src.target_strm_path,
    cd2_mount_prefix: src.cd2_mount_prefix,
    media_type: src.media_type,
    enabled: src.enabled,
    strm_mode: src.strm_mode,
    webdav_base_url: src.webdav_base_url || "",
    webdav_path_prefix: src.webdav_path_prefix || "",
    strm_extensions: src.strm_extensions,
    metadata_extensions: src.metadata_extensions,
    scrape_enabled: src.scrape_enabled,
    same_as_source: src.source_path === src.cd2_mount_prefix,
  };
  message.success(`已从「${src.name}」复制配置, 修改名称后保存`);
}

// 联动: same_as_source 勾选时 cd2_mount_prefix 跟随 source_path
watch(() => [form.value.source_path, form.value.same_as_source], () => {
  if (form.value.same_as_source) {
    form.value.cd2_mount_prefix = form.value.source_path;
  }
}, { immediate: true });

async function load() {
  loading.value = true;
  try { libs.value = await listLibraries(); } finally { loading.value = false; }
}

async function submit() {
  if (!form.value.name || !form.value.source_path || !form.value.target_strm_path) {
    message.warning("请填完必填项"); return;
  }
  if (form.value.strm_mode === "webdav" && !form.value.webdav_base_url) {
    message.warning("WebDAV 模式需要 base_url"); return;
  }
  const payload: any = { ...form.value };
  delete payload.same_as_source;
  if (payload.strm_mode !== "webdav") {
    payload.webdav_base_url = null;
    payload.webdav_path_prefix = null;
  }
  try {
    if (editingLib.value) {
      await updateLibrary(editingLib.value.id, payload);
      message.success("已保存");
    } else {
      await createLibrary(payload);
      message.success("创建成功");
    }
    showCreate.value = false;
    resetModal();
    await load();
  } catch (e: any) {
    message.error((editingLib.value ? "保存" : "创建") + "失败: " + (e?.response?.data?.detail || e.message));
  }
}

function onEdit(lib: Library) {
  editingLib.value = lib;
  form.value = {
    name: lib.name,
    source_path: lib.source_path,
    target_strm_path: lib.target_strm_path,
    cd2_mount_prefix: lib.cd2_mount_prefix,
    media_type: lib.media_type,
    enabled: lib.enabled,
    strm_mode: lib.strm_mode,
    webdav_base_url: lib.webdav_base_url || "",
    webdav_path_prefix: lib.webdav_path_prefix || "",
    strm_extensions: lib.strm_extensions,
    metadata_extensions: lib.metadata_extensions,
    scrape_enabled: lib.scrape_enabled,
    same_as_source: lib.source_path === lib.cd2_mount_prefix,
  };
  showCreate.value = true;
}

function resetModal() {
  editingLib.value = null;
  form.value = defaultForm();
  cloneFromId.value = null;
}

function onModalClose(v: boolean) {
  showCreate.value = v;
  if (!v) resetModal();
}

async function onScan(lib: Library) {
  try { const t = await startScan(lib.id); message.success(`扫描已入队 task #${t.id}`); }
  catch (e: any) { message.error("扫描启动失败: " + (e?.response?.data?.detail || e.message)); }
}

async function onDelete(lib: Library) {
  await deleteLibrary(lib.id);
  message.success("删除成功");
  await load();
}

const isWebdav = computed(() => form.value.strm_mode === "webdav");

function timeAgo(iso: string | null): string {
  if (!iso) return "从未";
  const diff = Date.now() - new Date(iso).getTime();
  const min = Math.floor(diff / 60000);
  if (min < 1) return "刚刚";
  if (min < 60) return `${min} 分钟前`;
  const h = Math.floor(min / 60);
  if (h < 24) return `${h} 小时前`;
  const d = Math.floor(h / 24);
  return `${d} 天前`;
}

const typeIcon = (t: string) => t === "tv" ? TvOutline : t === "mixed" ? AlbumsOutline : FilmOutline;

const columns: DataTableColumns<Library> = [
  {
    title: "状态", key: "_status", width: 60,
    render(row) {
      return h(NTooltip, {}, {
        trigger: () => h(NIcon, {
          component: EllipseSharp, color: row.enabled ? "#22c55e" : "#9ca3af", size: 12,
        }),
        default: () => row.enabled ? "已启用" : "已停用",
      });
    },
  },
  { title: "ID", key: "id", width: 50 },
  {
    title: "名称", key: "name", minWidth: 160,
    render(row) {
      return h("div", { style: "display: flex; align-items: center; gap: 8px;" }, [
        h(NIcon, { component: typeIcon(row.media_type), size: 18, color: "#5b8def" }),
        h("span", { style: "font-weight: 500;" }, row.name),
      ]);
    },
  },
  { title: "扫描源", key: "source_path", ellipsis: { tooltip: true } },
  { title: "strm 输出", key: "target_strm_path", ellipsis: { tooltip: true } },
  {
    title: "strm 模式", key: "strm_mode", width: 110,
    render(row) {
      return h(NTag, {
        size: "small", round: true,
        type: row.strm_mode === "webdav" ? "warning" : "info",
      }, {
        icon: () => h(NIcon, { component: row.strm_mode === "webdav" ? CloudOutline : FolderOpenOutline }),
        default: () => row.strm_mode,
      });
    },
  },
  {
    title: "刮削", key: "scrape_enabled", width: 70,
    render(row) {
      return h(NTag, {
        size: "small", round: true,
        type: row.scrape_enabled ? "success" : "default",
      }, { default: () => row.scrape_enabled ? "开" : "关" });
    },
  },

  {
    title: "最近扫描", key: "last_scan_at", width: 110,
    render(row) {
      return h("span", { style: row.last_scan_at ? "" : "opacity: 0.5;" }, timeAgo(row.last_scan_at));
    },
  },
  {
    title: "操作", key: "actions", width: 220,
    render(row) {
      return h(NSpace, { size: 6 }, () => [
        h(NButton, { size: "small", type: "primary", onClick: () => onScan(row) }, {
          icon: () => h(NIcon, { component: PlayOutline }),
          default: () => "扫描",
        }),
        h(NButton, { size: "small", quaternary: true, onClick: () => onEdit(row) }, {
          icon: () => h(NIcon, { component: CreateOutline }),
        }),
        h(NPopconfirm, { onPositiveClick: () => onDelete(row) }, {
          default: () => "确认删除?",
          trigger: () => h(NButton, { size: "small", type: "error", quaternary: true }, {
            icon: () => h(NIcon, { component: TrashOutline }),
          }),
        }),
      ]);
    },
  },
];

onMounted(load);
</script>

<template>
  <n-card title="媒体库" style="border-radius: 14px;">
    <template #header-extra>
      <n-button type="primary" @click="showCreate = true">
        <template #icon><n-icon :component="AddOutline" /></template>
        新建
      </n-button>
    </template>
    <n-data-table :columns="columns" :data="libs" :loading="loading" :bordered="false" />
  </n-card>

  <n-modal :show="showCreate" preset="card" :title="isEditing ? '编辑媒体库 — ' + editingLib?.name : '新建媒体库'" style="width: 640px;" @update:show="onModalClose">
    <n-form label-placement="top">
      <n-form-item v-if="!isEditing && cloneOptions.length" label="复制现有配置" :feedback="'选择已有库, 自动填入除名称外所有字段'">
        <n-select
          v-model:value="cloneFromId"
          :options="cloneOptions"
          placeholder="(可选) 从已有库快速复制"
          clearable
          @update:value="copyFromLib"
        />
      </n-form-item>
      <n-form-item label="名称 *">
        <n-input v-model:value="form.name" placeholder="例: 我的电影库" />
      </n-form-item>
      <n-form-item label="扫描源路径 *" :feedback="'容器内的路径, 例 /scan-source/Movies'">
        <n-input v-model:value="form.source_path" placeholder="/scan-source/Movies" />
      </n-form-item>
      <n-form-item label="strm 输出路径 *" :feedback="'容器内的路径, 例 /media/电影'">
        <n-input v-model:value="form.target_strm_path" placeholder="/media/电影" />
      </n-form-item>

      <n-form-item label="strm 模式 *" :feedback="'cd2_local 写本地路径, webdav 写 URL'">
        <n-select v-model:value="form.strm_mode" :options="[
          { label: 'CD2 本地路径', value: 'cd2_local' },
          { label: 'WebDAV URL', value: 'webdav' },
        ]" />
      </n-form-item>
      <n-form-item v-if="!isWebdav" label="CD2 路径前缀 *" :feedback="'写进 .strm 的前缀, Emby 通过此回源'">
        <n-space vertical :size="8" style="width: 100%;">
          <n-checkbox v-model:checked="form.same_as_source">
            跟扫描源相同（Emby 跟 fystrm 看到同一个 /mnt 挂载）
          </n-checkbox>
          <n-input
            v-model:value="form.cd2_mount_prefix"
            placeholder="/CloudNAS/115/电影"
            :disabled="form.same_as_source"
          />
        </n-space>
      </n-form-item>
      <n-form-item v-if="isWebdav" label="WebDAV Base URL *" :feedback="'CD2 暴露的 WebDAV 服务地址'">
        <n-input v-model:value="form.webdav_base_url" placeholder="http://cd2:19798/dav" />
      </n-form-item>
      <n-form-item v-if="isWebdav" label="WebDAV 路径前缀" :feedback="'例 /115/电影'">
        <n-input v-model:value="form.webdav_path_prefix" placeholder="/115/电影" />
      </n-form-item>
      <n-form-item label="刮削" :feedback="form.scrape_enabled ? '调 TMDB 刮削, 生成 fystrm 自己的 movie.nfo + 海报' : '只生成 strm + 镜像源元数据, 不调 TMDB. 源没 nfo 就什么也没有'">
        <n-switch v-model:value="form.scrape_enabled">
          <template #checked>开启</template>
          <template #unchecked>关闭</template>
        </n-switch>
      </n-form-item>

      <n-form-item label="strm 后缀" :feedback="'分号分隔, 指定后缀的文件会生成 .strm. 例: .mp4;.mkv;.ts'">
        <n-input
          v-model:value="form.strm_extensions"
          type="textarea"
          :autosize="{ minRows: 2, maxRows: 4 }"
          placeholder=".mp4;.mkv;.ts"
        />
      </n-form-item>
      <n-form-item label="元数据后缀" :feedback="'分号分隔, 命中后缀的文件原样镜像到 strm 输出目录, 留空跳过. 例: .nfo;.jpg;.png'">
        <n-input
          v-model:value="form.metadata_extensions"
          type="textarea"
          :autosize="{ minRows: 2, maxRows: 4 }"
          placeholder=".nfo;.jpg;.png"
        />
      </n-form-item>
      <n-button type="primary" @click="submit" block size="large">
        <template #icon><n-icon :component="isEditing ? SaveOutline : AddOutline" /></template>
        {{ isEditing ? "保存" : "创建" }}
      </n-button>
    </n-form>
  </n-modal>
</template>
