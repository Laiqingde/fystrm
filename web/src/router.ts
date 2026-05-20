import { createRouter, createWebHashHistory } from "vue-router";

export const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: "/", redirect: "/dashboard" },
    { path: "/dashboard", component: () => import("./views/Dashboard.vue") },
    { path: "/libraries", component: () => import("./views/Libraries.vue") },
    { path: "/tasks", component: () => import("./views/TaskList.vue") },
    { path: "/media", component: () => import("./views/MediaList.vue") },
    { path: "/settings", component: () => import("./views/Settings.vue") },
  ],
});
