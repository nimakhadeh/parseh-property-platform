/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./templates/**/*.html",
        "./apps/**/templates/**/*.html",
    ],
    darkMode: "class",
    theme: {
        extend: {
            fontFamily: {
                vazir: ["Vazirmatn", "sans-serif"],
                display: ["Vazirmatn", "sans-serif"],
            },
            colors: {
                primary: { DEFAULT: "#0E5D50", dark: "#0A3F37", light: "rgb(var(--color-primary-light) / <alpha-value>)" },
                canvas: "rgb(var(--color-canvas) / <alpha-value>)",
                ink: "rgb(var(--color-ink) / <alpha-value>)",
                accent: { DEFAULT: "#C68A3D", dark: "#A8722E" },
                brick: { DEFAULT: "#B6512E", dark: "#8F3E22" },
                line: "rgb(var(--color-line) / <alpha-value>)",
            },
        },
    },
    plugins: [],
};
