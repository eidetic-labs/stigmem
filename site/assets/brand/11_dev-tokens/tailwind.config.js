// tailwind.config.js (Stigmem)
// Stigmem inherits indigo/violet from Tailwind's standard palette.
module.exports = {
  theme: {
    extend: {
      colors: {
        deep: "#070912",
        ink: "#0A0A0A",
        paper: "#FFFFFF",
        // Indigo/violet are the brand accents — same hex as Tailwind's
        // indigo-400 / violet-400 / violet-300 for easy integration.
      },
      fontFamily: {
        sans: ["Poppins", "system-ui", "-apple-system", "sans-serif"],
      },
      letterSpacing: { wordmark: "0.28em", eyebrow: "0.22em" },
      borderRadius: { sm: "6px", md: "12px", lg: "20px" },
    },
  },
};
