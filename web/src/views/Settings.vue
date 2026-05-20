<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import {
  NCard, NDescriptions, NDescriptionsItem, NTag, NAlert, NButton, NIcon, NInput,
  NSpace, NSpin, NCode, useMessage,
} from "naive-ui";
import {
  RefreshOutline, InformationCircleOutline, CopyOutline, KeyOutline,
  LinkOutline, EyeOutline, EyeOffOutline,
} from "@vicons/ionicons5";
import { getSettings, type Settings } from "../api";

const message = useMessage();
const s = ref<Settings | null>(null);
const baseUrl = ref<string>("");
const showToken = ref(false);

async function load() {
  s.value = await getSettings();
  if (!baseUrl.value) {
    baseUrl.value = `${window.location.protocol}//${window.location.host}`;
  }
}

function genTOML(bu: string, token: string): string {
  const tokenLine = token ? `Bearer ${token}` : `Bearer 在服务器 .env 配置 CD2_WEBHOOK_TOKEN`;
  return `# CD2 webhook 配置 (粘贴到 CloudDrive2 webhook 配置文件)
# 由 fystrm 自动生成

[global_params]
base_url = "${bu}"
enabled = true
time_format = "rfc3339"

[global_params.default_headers]
content-type = "application/json"
user-agent = "clouddrive2/{version}"
authorization = "${tokenLine}"


# === 文件变更 webhook ===
[file_system_watcher]
url = "{base_url}/api/webhooks/cd2/file?device={device_name}&user={user_name}"
method = "POST"
enabled = true
body = '''
{
    "device_name": "{device_name}",
    "user_name": "{user_name}",
    "version": "{version}",
    "event_category": "{event_category}",
    "event_name": "{event_name}",
    "event_time": "{event_time}",
    "send_time": "{send_time}",
    "data": [
        {
            "action": "{action}",
            "is_dir": "{is_dir}",
            "source_file": "{source_file}",
            "destination_file": "{destination_file}"
        }
    ]
}
'''


# === 挂载点变更 webhook ===
[mount_point_watcher]
url = "{base_url}/api/webhooks/cd2/mount?device={device_name}&user={user_name}&type={event_name}"
method = "POST"
enabled = true
body = '''
{
    "device_name": "{device_name}",
    "user_name": "{user_name}",
    "version": "{version}",
    "event_category": "{event_category}",
    "event_name": "{event_name}",
    "event_time": "{event_time}",
    "send_time": "{send_time}",
    "data": [
        {
            "action": "{action}",
            "mount_point": "{mount_point}",
            "status": "{status}",
            "reason": "{reason}"
        }
    ]
}
'''
`;
}

const tomlPreview = computed(() => {
  if (!s.value) return "";
  return genTOML(baseUrl.value, s.value.cd2_webhook_token || "");
});

const maskedToken = computed(() => {
  const t = s.value?.cd2_webhook_token || "";
  if (!t) return "未配置";
  if (showToken.value) return t;
  return t.slice(0, 8) + "...".repeat(2) + t.slice(-8);
});

function copyText(text: string): boolean {
  // 优先用 modern API (HTTPS / localhost)
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).catch(() => {});
    return true;
  }
  // fallback: 临时 textarea + execCommand (老 API, http 也行)
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.style.position = "fixed";
  ta.style.left = "-9999px";
  ta.style.opacity = "0";
  document.body.appendChild(ta);
  ta.select();
  ta.setSelectionRange(0, text.length);
  let ok = false;
  try { ok = document.execCommand("copy"); } catch {}
  document.body.removeChild(ta);
  return ok;
}

async function copyTOML() {
  if (copyText(tomlPreview.value)) {
    message.success("已复制到剪贴板");
  } else {
    message.error("复制失败，请手动选择文本复制");
  }
}

async function copyToken() {
  if (!s.value?.cd2_webhook_token) return;
  if (copyText(s.value.cd2_webhook_token)) {
    message.success("Token 已复制");
  } else {
    message.error("复制失败");
  }
}

onMounted(load);
</script>

<template>
  <n-space vertical :size="20">
    <!-- 基础设置 -->
    <n-card title="设置" style="border-radius: 14px;">
      <n-alert type="info" style="margin-bottom: 20px;" :show-icon="true">
        <template #icon><n-icon :component="InformationCircleOutline" /></template>
        v0.2 设置只读，编辑请改服务器 <code>/opt/fystrm/.env</code> 后重启容器。
      </n-alert>
      <n-descriptions v-if="s" :column="2" bordered label-placement="left">
        <n-descriptions-item label="TMDB 已配置">
          <n-tag :type="s.tmdb_configured ? 'success' : 'error'" round>{{ s.tmdb_configured ? '是' : '否' }}</n-tag>
        </n-descriptions-item>
        <n-descriptions-item label="TMDB 语言">{{ s.tmdb_language }}</n-descriptions-item>
        <n-descriptions-item label="Emby 已配置">
          <n-tag :type="s.emby_configured ? 'success' : 'warning'" round>{{ s.emby_configured ? '是' : '未配置（不影响扫描+strm 生成）' }}</n-tag>
        </n-descriptions-item>
        <n-descriptions-item label="Emby URL">{{ s.emby_url || '—' }}</n-descriptions-item>
        <n-descriptions-item label="CD2 Webhook 已配置">
          <n-tag :type="s.cd2_webhook_configured ? 'success' : 'warning'" round>{{ s.cd2_webhook_configured ? '是' : '未配置' }}</n-tag>
        </n-descriptions-item>
        <n-descriptions-item label="日志级别">{{ s.log_level }}</n-descriptions-item>
      </n-descriptions>
      <div style="margin-top: 16px;">
        <n-button quaternary @click="load">
          <template #icon><n-icon :component="RefreshOutline" /></template>
          刷新
        </n-button>
      </div>
    </n-card>

    <!-- CD2 Webhook 配置预览 -->
    <n-card title="CD2 Webhook 配置" style="border-radius: 14px;">
      <template #header-extra>
        <n-tag :type="s?.cd2_webhook_configured ? 'success' : 'warning'" size="small" round>
          {{ s?.cd2_webhook_configured ? '已就绪' : '未生成 Token' }}
        </n-tag>
      </template>

      <n-alert type="info" :show-icon="true" style="margin-bottom: 16px;">
        <template #icon><n-icon :component="InformationCircleOutline" /></template>
        把下面的 TOML 配置粘贴到 CloudDrive2 的 webhook 配置文件中即可。
        文件路径通常是 <code>/Config/cloudd/webhooks.toml</code>。
        粘贴后重启 CD2 生效。
      </n-alert>

      <!-- Base URL 可编辑 -->
      <div style="margin-bottom: 14px;">
        <div style="font-weight: 500; margin-bottom: 6px;">
          <n-icon :component="LinkOutline" :size="16" style="vertical-align: -3px;" />
          fystrm 访问地址 (CD2 推 webhook 用的)
        </div>
        <n-input
          v-model:value="baseUrl"
          placeholder="http://192.200.102.58:8095"
        />
        <div style="font-size: 12px; opacity: 0.6; margin-top: 4px;">
          默认 = 当前浏览器访问的地址。如果 CD2 在另一台机器需要走公网/内网 IP，请改为 CD2 那台机器能访问到的地址。
        </div>
      </div>

      <!-- Token 显示 + 复制 -->
      <div style="margin-bottom: 16px;">
        <div style="font-weight: 500; margin-bottom: 6px;">
          <n-icon :component="KeyOutline" :size="16" style="vertical-align: -3px;" />
          Webhook Token
        </div>
        <n-space :wrap="false">
          <n-input :value="maskedToken" readonly style="font-family: ui-monospace, Menlo, Consolas, monospace;" />
          <n-button @click="showToken = !showToken" quaternary>
            <template #icon><n-icon :component="showToken ? EyeOffOutline : EyeOutline" /></template>
          </n-button>
          <n-button @click="copyToken" :disabled="!s?.cd2_webhook_token">
            <template #icon><n-icon :component="CopyOutline" /></template>
            复制
          </n-button>
        </n-space>
        <div v-if="!s?.cd2_webhook_configured" style="font-size: 12px; color: #ef4444; margin-top: 4px;">
          ⚠️ 服务器 .env 里还没设 CD2_WEBHOOK_TOKEN, webhook 端点会返回 503
        </div>
      </div>

      <!-- TOML 预览 + 复制 -->
      <div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
          <div style="font-weight: 500;">TOML 配置预览</div>
          <n-button @click="copyTOML" type="primary" size="small">
            <template #icon><n-icon :component="CopyOutline" /></template>
            复制全部
          </n-button>
        </div>
        <n-code :code="tomlPreview" language="toml" word-wrap show-line-numbers />
      </div>
    </n-card>
  </n-space>
</template>
