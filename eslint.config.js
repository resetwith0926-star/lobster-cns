import astro from "eslint-plugin-astro";
import globals from "globals";

export default [
  {
    ignores: [
      "dist",
      ".astro",
      "node_modules",
      "lobster-cns/**",
      "VoxCPM/**",
      "tools/**",
    ],
  },
  ...astro.configs["flat/recommended"],
  {
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
  },
];
