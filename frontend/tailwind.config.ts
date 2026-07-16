import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // ── Rose Pink Medical Palette ──
        rose: {
          50: "#fef6f9",
          100: "#fde8ef",
          200: "#fbd1df",
          300: "#f7aac5",
          400: "#f07ba3",
          500: "#e88ba7",
          600: "#d4678a",
          700: "#b84d6e",
          800: "#9a405c",
          900: "#813a50",
          950: "#4c1c2b",
        },
        // Warm cream/beige — backgrounds
        cream: {
          50: "#fffdfb",
          100: "#fff9f5",
          200: "#fff2eb",
          300: "#fce8db",
          400: "#f5d5c0",
          500: "#ecc1a4",
          600: "#dba583",
          700: "#c48a65",
          800: "#a47254",
          900: "#8a6148",
        },
        // Medical blue — accents
        medical: {
          50: "#f2f7fb",
          100: "#e4eef7",
          200: "#c9ddf0",
          300: "#a2c6e3",
          400: "#7aaad3",
          500: "#8bb8d9",
          600: "#4d91bf",
          700: "#3b75a5",
          800: "#346188",
          900: "#2f5171",
        },
        // Soft green — safety indicators
        sage: {
          50: "#f4f9f6",
          100: "#e6f1ea",
          200: "#cee3d7",
          300: "#a8d5ba",
          400: "#7dba98",
          500: "#5ca07b",
          600: "#498463",
          700: "#3c6a50",
          800: "#345542",
          900: "#2c4638",
        },
        // EHS Risk colors
        ehs: {
          critical: "#991b1b",
          high: "#c2410c",
          moderate: "#b45309",
          low: "#15803d",
          safe: "#0d9488",
          unknown: "#78716c",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          '"Helvetica Neue"',
          "Arial",
          "sans-serif",
        ],
        mono: ["JetBrains Mono", "Fira Code", "Consolas", "monospace"],
      },
      fontSize: {
        "2xs": ["0.6875rem", { lineHeight: "1rem" }],
        "3xs": ["0.625rem", { lineHeight: "0.875rem" }],
      },
      borderRadius: {
        "4xl": "2rem",
      },
      boxShadow: {
        soft: "0 2px 15px -3px rgba(0,0,0,0.04), 0 1px 2px -1px rgba(0,0,0,0.02)",
        card: "0 1px 3px rgba(0,0,0,0.03), 0 1px 2px rgba(0,0,0,0.02)",
        elevated: "0 4px 24px -6px rgba(0,0,0,0.06), 0 2px 8px -4px rgba(0,0,0,0.03)",
      },
      animation: {
        "fade-in": "fadeIn 0.4s ease-out",
        "slide-up": "slideUp 0.4s ease-out",
        "expand-down": "expandDown 0.3s ease-out",
        float: "float 6s ease-in-out infinite",
      },
      keyframes: {
        fadeIn: { "0%": { opacity: "0" }, "100%": { opacity: "1" } },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        expandDown: {
          "0%": { opacity: "0", transform: "scaleY(0.95)", maxHeight: "0" },
          "100%": { opacity: "1", transform: "scaleY(1)", maxHeight: "2000px" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-10px)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
