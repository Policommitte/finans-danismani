/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/app/**/*.{js,jsx,ts,tsx}",
    "./src/components/**/*.{js,jsx,ts,tsx}",
    "./src/hooks/**/*.{js,jsx,ts,tsx}",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        eggshell: "#f4f1de",
        "burnt-peach": "#e07a5f",
        "twilight-indigo": "#3d405b",
        "muted-teal": "#81b29a",
        "apricot-cream": "#f2cc8f",
      },
    },
  },
  plugins: [],
}
