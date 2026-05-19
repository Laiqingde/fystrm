import { computed, ref, watchEffect } from "vue";
import { darkTheme, lightTheme, type GlobalThemeOverrides } from "naive-ui";

export type ThemeMode = "auto" | "light" | "dark";

const STORAGE_KEY = "fystrm-theme-mode";
const stored = (localStorage.getItem(STORAGE_KEY) as ThemeMode) || "auto";
export const themeMode = ref<ThemeMode>(stored);

const systemDark = ref(window.matchMedia("(prefers-color-scheme: dark)").matches);
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (e) => {
  systemDark.value = e.matches;
});

export const isDark = computed(() => {
  if (themeMode.value === "dark") return true;
  if (themeMode.value === "light") return false;
  return systemDark.value;
});

export const naiveTheme = computed(() => (isDark.value ? darkTheme : lightTheme));

export const themeOverrides = computed<GlobalThemeOverrides>(() => {
  const accent = "#5b8def";       // 主蓝色
  const accentHover = "#7da5f5";
  const accentPressed = "#3f6dd6";
  return {
    common: {
      primaryColor: accent,
      primaryColorHover: accentHover,
      primaryColorPressed: accentPressed,
      primaryColorSuppl: accent,
      borderRadius: "8px",
      borderRadiusSmall: "6px",
      fontWeightStrong: "600",
      ...(isDark.value
        ? {
            bodyColor: "#0e1117",
            cardColor: "#161b22",
            modalColor: "#1c2128",
            popoverColor: "#1c2128",
            tableHeaderColor: "#1c2128",
            dividerColor: "rgba(255,255,255,0.06)",
            borderColor: "rgba(255,255,255,0.08)",
            tagColor: "#21262d",
            textColorBase: "#e6edf3",
            textColor1: "#e6edf3",
            textColor2: "#c9d1d9",
            textColor3: "#8b949e",
          }
        : {
            bodyColor: "#f5f7fb",
            cardColor: "#ffffff",
            modalColor: "#ffffff",
            popoverColor: "#ffffff",
            tableHeaderColor: "#f8fafc",
          }),
    },
    Card: {
      paddingMedium: "20px 24px",
    },
    Layout: {
      headerColor: isDark.value ? "#0e1117" : "#ffffff",
      headerBorderColor: isDark.value ? "rgba(255,255,255,0.08)" : "#e5e7eb",
    },
    Button: {
      fontWeight: "500",
    },
  };
});

export function setThemeMode(mode: ThemeMode) {
  themeMode.value = mode;
  localStorage.setItem(STORAGE_KEY, mode);
}

// 同步到 <html class="dark|light"> 方便 CSS 变量响应
watchEffect(() => {
  const html = document.documentElement;
  html.classList.toggle("dark", isDark.value);
  html.classList.toggle("light", !isDark.value);
});
