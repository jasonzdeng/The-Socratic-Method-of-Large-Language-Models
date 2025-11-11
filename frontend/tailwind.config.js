/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: "#f5f3ff",
          500: "#6366f1",
          700: "#4338ca"
        }
      }
    }
  },
  plugins: []
};
