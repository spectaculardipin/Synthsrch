/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: { serif: ["Georgia", "Times New Roman", "serif"] },
      borderRadius: { card: "20px" },
    },
  },
  plugins: [],
};
