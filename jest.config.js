const { clear } = require("console");

module.exports = {
    clearMocks: true,
    collectCoverageFrom: [
        "**/*.{js,jsx,ts,tsx}",
        "!**/*.d.ts",
        "!**/node_modules/**",
        "!**/lcov/**",
        "!**/coverage/**",
        "!**/htmlcov/**",
        "!**/.venv/**",
        "!./*.js",
        "!./*.json",
        "!**/docs/**",
    ],
    coverageProvider: "v8",
    coverageReporters: ["json", "lcov", "text", "clover"],
    coverageThreshold: {
        global: {
            branches: 80,
            functions: 80,
            lines: 80,
            statements: 80
        }
    },
    moduleFileExtensions: ["js", "json", "jsx", "ts", "tsx", "node"],
    testEnvironment: "node",
}