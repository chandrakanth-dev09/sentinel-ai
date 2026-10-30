/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#0b111c",
        panel: "#111a28",
        line: "#243246",
        accent: "#48d6b5"
      }
    }
  },
  plugins: []
};
