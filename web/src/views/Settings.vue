<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import {
  NCard, NSpace, NButton, NIcon, NInput, NSelect, NTag, NDivider, NSwitch,
  NAlert, NEmpty, NSpin, NModal, NForm, NFormItem, useMessage,
} from "naive-ui";
import {
  KeyOutline, CloudOutline, NotificationsOutline, FilmOutline,
  ServerOutline, ShieldOutline, EyeOutline, EyeOffOutline,
  SaveOutline, CopyOutline, InformationCircleOutline, LockClosedOutline,
} from "@vicons/ionicons5";
import { api } from "../api";

interface FieldMeta { value: string; is_secret: boolean; configured: boolean }
interface SettingsResp { fields: Record<string, FieldMeta>; static: any }

const message = useMessage();
const loading = ref(true);
const saving = ref(false);
const data = ref<SettingsResp | null>(null);

// 各字段编辑值 (string)
const form = ref<Record<string, string>>({});
const reveal = ref<Record<string, boolean>>({});

// 修改密码 modal
const showPwdModal = ref(false);
const pwdForm = ref({ old_password: "", new_password: "", confirm: "" });
const pwdSaving = ref(false);

// 字段定义 + 分组 + 元信息
const groups = computed(() => [
  {
    title: "TMDB 刮削源", icon: FilmOutline, color: "#5b8def",
    keys: ["TMDB_API_KEY", "TMDB_LANGUAGE"],
    hint: "从 themoviedb.org 申请 API Key, 影响电影/剧集元数据刮削",
  },
  {
    title: "Emby 集成", icon: CloudOutline, color: "#22c55e",
    keys: ["EMBY_URL", "EMBY_API_KEY"],
    hint: "扫描完成后自动触发 Emby 库刷新, 不配也不影响 strm 生成",
  },
  {
    title: "CD2 Webhook", icon: NotificationsOutline, color: "#06b6d4",
    keys: ["CD2_WEBHOOK_TOKEN", "CD2_MOUNT_ROOT"],
    hint: "CD2 推送文件变更 -> fystrm 增量入库. Token 配在 CD2 的 webhook.toml authorization 头",
  },
  {
    title: "日志", icon: ServerOutline, color: "#f59e0b",
    keys: ["LOG_LEVEL"],
    hint: "日志输出级别, 实时日志页 INFO+ 才推送",
  },
]);

const fieldLabel: Record<string, string> = {
  TMDB_API_KEY: "TMDB API Key",
  TMDB_LANGUAGE: "TMDB 语言",
  EMBY_URL: "Emby URL",
  EMBY_API_KEY: "Emby API Key",
  CD2_WEBHOOK_TOKEN: "Webhook Token",
  CD2_MOUNT_ROOT: "CD2 容器挂载根",
  LOG_LEVEL: "日志级别",
};

const fieldPlaceholder: Record<string, string> = {
  TMDB_API_KEY: "32 位 API Key",
  TMDB_LANGUAGE: "zh-CN / en-US ...",
  EMBY_URL: "http://emby:8096",
  EMBY_API_KEY: "Emby admin 生成的 API Key",
  CD2_WEBHOOK_TOKEN: "Bearer token, 跟 CD2 toml authorization 头一致",
  CD2_MOUNT_ROOT: "/mnt/CloudNAS",
  LOG_LEVEL: "DEBUG / INFO / WARNING / ERROR",
};

async function load() {
  loading.value = true;
  try {
    const r = await api.get<SettingsResp>("/api/settings/");
    data.value = r.data;
    // 初始化 form
    for (const k in r.data.fields) {
      form.value[k] = r.data.fields[k].value || "";
    }
  } catch (e: any) {
    message.error("加载配置失败: " + (e?.response?.data?.detail || e.message));
  } finally {
    loading.value = false;
  }
}

async function saveGroup(keys: string[]) {
  saving.value = true;
  try {
    const payload: Record<string, string> = {};
    for (const k of keys) {
      // 如果当前显示的是打码值, 用户没改动 -> 不提交
      const orig = data.value?.fields[k];
      const cur = form.value[k] || "";
      if (orig?.is_secret && cur === orig.value && !reveal.value[k]) continue;
      payload[k] = cur;
    }
    if (!Object.keys(payload).length) {
      message.info("没有改动需要保存");
      saving.value = false;
      return;
    }
    await api.put("/api/settings/", { values: payload });
    message.success("已保存");
    await load();
  } catch (e: any) {
    message.error("保存失败: " + (e?.response?.data?.detail || e.message));
  } finally {
    saving.value = false;
  }
}

async function toggleReveal(k: string) {
  if (!reveal.value[k]) {
    // 拉明文
    try {
      const r = await api.get<SettingsResp>("/api/settings/?reveal=true");
      form.value[k] = r.data.fields[k].value || "";
      reveal.value[k] = true;
    } catch (e: any) {
      message.error("无权查看明文");
    }
  } else {
    reveal.value[k] = false;
    form.value[k] = data.value?.fields[k].value || "";
  }
}

async function copyValue(k: string) {
  let v = form.value[k];
  // 如果是 secret + 没显示明文, 先拉明文
  if (data.value?.fields[k].is_secret && !reveal.value[k]) {
    const r = await api.get<SettingsResp>("/api/settings/?reveal=true");
    v = r.data.fields[k].value;
  }
  if (!v) { message.warning("空值"); return; }
  // fallback copy
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(v);
  } else {
    const ta = document.createElement("textarea");
    ta.value = v; ta.style.position = "fixed"; ta.style.left = "-9999px";
    document.body.appendChild(ta); ta.select(); document.execCommand("copy"); document.body.removeChild(ta);
  }
  message.success("已复制");
}

async function submitPwd() {
  if (!pwdForm.value.old_password || !pwdForm.value.new_password) {
    message.warning("请填完整"); return;
  }
  if (pwdForm.value.new_password !== pwdForm.value.confirm) {
    message.warning("两次新密码不一致"); return;
  }
  if (pwdForm.value.new_password.length < 6) {
    message.warning("新密码至少 6 位"); return;
  }
  pwdSaving.value = true;
  try {
    await api.post("/api/settings/change-password", {
      old_password: pwdForm.value.old_password,
      new_password: pwdForm.value.new_password,
    });
    message.success("密码已更新, 下次登录用新密码");
    showPwdModal.value = false;
    pwdForm.value = { old_password: "", new_password: "", confirm: "" };
  } catch (e: any) {
    message.error(e?.response?.data?.detail || e.message);
  } finally {
    pwdSaving.value = false;
  }
}

// CD2 toml 预览
const tomlBaseUrl = ref("");
const tomlPreview = computed(() => {
  const token = (data.value?.fields["CD2_WEBHOOK_TOKEN"]?.value &&
                 !data.value.fields["CD2_WEBHOOK_TOKEN"].is_secret) ? "******" :
                (form.value.CD2_WEBHOOK_TOKEN || "未配置");
  const bu = tomlBaseUrl.value || `${location.protocol}//${location.host}`;
  return `[global_params]
base_url = "${bu}"
enabled = true
time_format = "rfc3339"

[global_params.default_headers]
authorization = "Bearer <去掉 reveal 才看得到 token>"
content-type = "application/json"

[file_system_watcher]
url = "{base_url}/api/webhooks/cd2/file"
method = "POST"
enabled = true

[mount_point_watcher]
url = "{base_url}/api/webhooks/cd2/mount"
method = "POST"
enabled = true`;
});

onMounted(() => {
  load();
  tomlBaseUrl.value = `${location.protocol}//${location.host}`;
});
</script>

<template>
  <n-spin :show="loading">
    <n-space vertical :size="20">
      <!-- 各分组 -->
      <n-card v-for="g in groups" :key="g.title" :title="g.title" style="border-radius: 14px;">
        <template #header-extra>
          <n-button type="primary" size="small" :loading="saving" @click="saveGroup(g.keys)">
            <template #icon><n-icon :component="SaveOutline" /></template>
            保存
          </n-button>
        </template>
        <template #header>
          <span style="display: inline-flex; align-items: center; gap: 8px;">
            <n-icon :component="g.icon" :size="20" :color="g.color" />
            <span>{{ g.title }}</span>
          </span>
        </template>

        <n-alert v-if="g.hint" type="info" :show-icon="false" style="margin-bottom: 16px; font-size: 13px;">
          {{ g.hint }}
        </n-alert>

        <n-form label-placement="left" label-width="160" :show-feedback="false">
          <n-form-item v-for="k in g.keys" :key="k" :label="fieldLabel[k] || k">
            <n-space :wrap="false" style="width: 100%;">
              <n-input
                v-model:value="form[k]"
                :type="data?.fields[k]?.is_secret && !reveal[k] ? 'password' : 'text'"
                :placeholder="fieldPlaceholder[k]"
                style="flex: 1; min-width: 200px;"
              />
              <n-button v-if="data?.fields[k]?.is_secret" quaternary @click="toggleReveal(k)">
                <template #icon><n-icon :component="reveal[k] ? EyeOffOutline : EyeOutline" /></template>
              </n-button>
              <n-button quaternary @click="copyValue(k)">
                <template #icon><n-icon :component="CopyOutline" /></template>
              </n-button>
            </n-space>
          </n-form-item>
        </n-form>
      </n-card>

      <!-- 安全分组 -->
      <n-card title="账号安全" style="border-radius: 14px;">
        <template #header>
          <span style="display: inline-flex; align-items: center; gap: 8px;">
            <n-icon :component="ShieldOutline" :size="20" color="#ef4444" />
            <span>账号安全</span>
          </span>
        </template>
        <n-space vertical>
          <n-button type="warning" @click="showPwdModal = true">
            <template #icon><n-icon :component="LockClosedOutline" /></template>
            修改管理员密码
          </n-button>
          <span style="font-size: 12px; opacity: 0.6;">登录密码独立于其他配置, 单独修改</span>
        </n-space>
      </n-card>
    </n-space>
  </n-spin>

  <!-- 修改密码 Modal -->
  <n-modal v-model:show="showPwdModal" preset="card" title="修改管理员密码" style="width: 460px;">
    <n-form label-placement="top">
      <n-form-item label="原密码">
        <n-input v-model:value="pwdForm.old_password" type="password" show-password-on="click" />
      </n-form-item>
      <n-form-item label="新密码 (至少 6 位)">
        <n-input v-model:value="pwdForm.new_password" type="password" show-password-on="click" />
      </n-form-item>
      <n-form-item label="确认新密码">
        <n-input v-model:value="pwdForm.confirm" type="password" show-password-on="click" @keyup.enter="submitPwd" />
      </n-form-item>
      <n-button type="primary" block :loading="pwdSaving" @click="submitPwd">提交</n-button>
    </n-form>
  </n-modal>
</template>
