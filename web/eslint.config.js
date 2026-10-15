export default [
  {
    // ignore lint for mediainfo source code
    ignores: ["mediainfo.js/**"],
  },
  {
    // browser main thread code
    files: ["app.js", "scanner.js", "native.js", "wasm.js", "utils.js"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: {
        window: "readonly",
        document: "readonly",
        URL: "readonly",
        fetch: "readonly",
        Worker: "readonly",
        setTimeout: "readonly",
        clearTimeout: "readonly",
        console: "readonly",
        alert: "readonly",
        location: "readonly",
        navigator: "readonly",
      },
    },
    rules: {
      "no-undef": "error",
      eqeqeq: "error",
      "no-var": "error",
      radix: "error",
      "no-async-promise-executor": "error",
      "no-unused-vars": "warn",
      "no-console": ["warn", { allow: ["warn", "error"] }],
    },
  },
  {
    // worker code
    files: ["mediainfo-worker.js"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "script",
      globals: {
        self: "readonly",
        importScripts: "readonly",
        postMessage: "readonly",
        console: "readonly",
        MediaInfo: "readonly",
      },
    },
    rules: {
      "no-undef": "error",
      eqeqeq: "error",
      "no-var": "error",
      "no-unused-vars": "warn",
      "no-console": ["warn", { allow: ["warn", "error"] }],
    },
  },
];
