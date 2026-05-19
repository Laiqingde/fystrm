import { createApp } from "vue";
import naive from "naive-ui";
import App from "./App.vue";
import { router } from "./router";

createApp(App).use(naive).use(router).mount("#app");
