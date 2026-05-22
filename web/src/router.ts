import { createRouter, createWebHashHistory } from "vue-router";
import { getToken } from "./api";

export const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: "/", redirect: "/dashboard" },
    { path: "/login", component: () => import("./views/Login.vue"), meta: { public: true } },
    { path: "/dashboard", component: () => import("./views/Dashboard.vue") },
    { path: "/libraries", component: () => import("./views/Libraries.vue") },
    { path: "/tasks", component: () => import("./views/TaskList.vue") },
    { path: "/media", component: () => import("./views/MediaList.vue") },
    { path: "/logs", component: () => import("./views/Logs.vue") },
    { path: "/settings", component: () => import("./views/Settings.vue") },
  ],
});

router.beforeEach((to, _from, next) => {
  if (to.meta?.public) { next(); return; }
  if (!getToken()) {
    next({ path: "/login", query: { redirect: to.fullPath } });
    return;
  }
  next();
});
