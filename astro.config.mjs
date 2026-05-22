import { defineConfig } from "astro/config";
import sitemap from "@astrojs/sitemap";

export default defineConfig({
  site: "https://cnfcd.tw",
  integrations: [sitemap()],
  output: "static",
});
