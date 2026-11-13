import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-bengali)", "var(--font-latin)", "sans-serif"],
      },
      colors: {
        paper: "#F8F7F4",
        ink: "#1E293B",
        emerald: {
          750: "#0F5132",
        },
      },
    },
  },
  plugins: [],
};

export default config;
