/**
 * AgentKit CLI — Platform-Aware Installer
 * Runs `npx agentkit init` flow: detect → select → install.
 */

"use strict";

const { execSync, spawnSync } = require("child_process");
const fs   = require("fs");
const path = require("path");
const { detectPlatforms, primaryPlatform } = require("./detect-platform");

// ---------------------------------------------------------------------------
// Skill bundles
// ---------------------------------------------------------------------------

const BUNDLES = {
  "backend-pro": {
    name: "Backend Pro",
    description: "Python/Go APIs, SQL/NoSQL, auth, security, DevOps",
    skills: [
      "debugging-python", "go-debugger", "tdd-workflow", "pytest-workflow",
      "rest-api", "grpc", "openapi-design", "webhook-design",
      "sql-query", "prisma-orm", "mongodb", "redis-caching", "database-migrations",
      "auth-jwt", "owasp-top10", "api-security", "secrets-management",
      "clean-code", "docker", "github-actions", "nginx-config", "performance-optimization",
    ],
  },
  "frontend-wizard": {
    name: "Frontend Wizard",
    description: "React/Vue/Next.js, CSS, state, a11y, E2E testing",
    skills: [
      "debugging-js", "jest-testing", "cypress-e2e", "playwright-testing", "tdd-workflow",
      "react-patterns", "vue-patterns", "nextjs-patterns", "css-layout",
      "state-management", "accessibility", "graphql", "clean-code",
    ],
  },
  "full-stack-hero": {
    name: "Full-Stack Hero",
    description: "All 50 skills",
    skills: [
      "debugging-python", "debugging-js", "go-debugger", "network-debugger",
      "tdd-workflow", "jest-testing", "pytest-workflow", "cypress-e2e", "playwright-testing", "contract-testing",
      "rest-api", "graphql", "grpc", "openapi-design", "webhook-design",
      "sql-query", "prisma-orm", "mongodb", "redis-caching", "database-migrations",
      "react-patterns", "nextjs-patterns", "css-layout", "vue-patterns", "state-management", "accessibility",
      "docker", "kubernetes", "github-actions", "terraform", "monitoring-observability", "nginx-config",
      "auth-jwt", "owasp-top10", "secrets-management", "api-security",
      "clean-code", "performance-optimization", "code-review", "legacy-modernization",
      "llm-prompting", "rag-pipeline", "function-calling", "agent-design", "eval-testing",
      "pandas-workflow", "data-visualization", "ml-pipeline",
      "react-native", "flutter",
    ],
  },
  "ai-engineer": {
    name: "AI Engineer",
    description: "LLM prompting, RAG, agents, evals, function calling",
    skills: [
      "llm-prompting", "rag-pipeline", "function-calling", "agent-design", "eval-testing",
      "debugging-python", "pytest-workflow", "rest-api", "tdd-workflow", "clean-code",
    ],
  },
  "devops-master": {
    name: "DevOps Master",
    description: "Docker, K8s, CI/CD, Terraform, monitoring, nginx",
    skills: [
      "docker", "kubernetes", "github-actions", "terraform",
      "monitoring-observability", "nginx-config",
      "debugging-python", "sql-query", "secrets-management",
    ],
  },
  "data-scientist": {
    name: "Data Scientist",
    description: "Pandas, ML pipelines, data visualization, SQL",
    skills: [
      "pandas-workflow", "data-visualization", "ml-pipeline",
      "debugging-python", "sql-query", "tdd-workflow", "pytest-workflow",
    ],
  },
  "mobile-dev": {
    name: "Mobile Dev",
    description: "React Native, Flutter, REST APIs, auth",
    skills: [
      "react-native", "flutter", "rest-api", "auth-jwt",
      "jest-testing", "debugging-js", "state-management",
    ],
  },
};

// ---------------------------------------------------------------------------
// Python installer bridge
// ---------------------------------------------------------------------------

/**
 * Call the Python platform adapter to do the actual file installation.
 * Returns { success, filesWritten, error }.
 */
function runPythonInstaller(platformId, skillIds, agentKitHome) {
  const skillIdsStr = skillIds.join(",");
  const result = spawnSync(
    "python3",
    [
      path.join(agentKitHome, "cli", "installer_bridge.py"),
      "--platform", platformId,
      "--skills",   skillIdsStr,
      "--home",     agentKitHome,
    ],
    { encoding: "utf8", cwd: process.cwd() },
  );

  if (result.error) {
    return { success: false, filesWritten: [], error: result.error.message };
  }
  if (result.status !== 0) {
    return { success: false, filesWritten: [], error: result.stderr || "installer failed" };
  }

  try {
    return JSON.parse(result.stdout.trim());
  } catch {
    return { success: true, filesWritten: [], error: "" };
  }
}

// ---------------------------------------------------------------------------
// Main install flow
// ---------------------------------------------------------------------------

function install(options = {}) {
  const agentKitHome = options.agentKitHome
    || process.env.AGENTKIT_HOME
    || path.join(__dirname, "..");

  const silent = options.silent || false;

  function log(...args) { if (!silent) console.log(...args); }

  log("\nAgentKit Installer v0.5.4");
  log("─────────────────────────\n");

  // 1. Detect platforms
  log("Detecting platforms...");
  const detected = detectPlatforms();

  if (detected.length === 0) {
    log("  ○ No supported platforms detected.");
    log("  Install Claude Code (claude.ai/code) and re-run.\n");
    return { success: false, platforms: [] };
  }

  for (const p of detected) {
    const tier = p.tier === 1 ? "(full)" : p.tier === 2 ? "(partial)" : "(basic)";
    log(`  ✓ ${p.name} ${tier}`);
  }
  log("");

  // 2. Determine target platforms
  const targetPlatforms = options.platforms
    ? detected.filter(p => options.platforms.includes(p.id))
    : detected;

  // 3. Determine skill bundle
  const bundleKey = options.bundle || "backend-pro";
  const bundle    = BUNDLES[bundleKey] || BUNDLES["backend-pro"];
  log(`Using skill bundle: ${bundle.name} (${bundle.skills.length} skills)\n`);

  // 4. Install per platform
  const results = [];
  for (const platform of targetPlatforms) {
    log(`Installing for ${platform.name}...`);
    const result = runPythonInstaller(platform.id, bundle.skills, agentKitHome);

    if (result.success) {
      for (const f of (result.filesWritten || [])) {
        log(`  ✓ ${f}`);
      }
      results.push({ platform: platform.id, success: true });
    } else {
      log(`  ✗ ${result.error || "unknown error"}`);
      results.push({ platform: platform.id, success: false, error: result.error });
    }
    log("");
  }

  // 5. Summary
  const succeeded = results.filter(r => r.success);
  log("──────────────────────────────────────────────────");
  if (succeeded.length > 0) {
    log("✓ AgentKit installed successfully!\n");
    for (const r of succeeded) {
      log(`  ${r.platform}: installed`);
    }
    log("\n  Estimated savings:");
    log("    Tokens:  ~40,000 → ~5,000/session (89% reduction)");
    log("    Cost:    ~70% reduction vs default all-Sonnet\n");
    log("  Run: npx agentkit status   → view real-time stats");
    log("  Run: npx agentkit costs    → view cost analytics");
  } else {
    log("✗ Installation failed for all platforms.");
  }
  log("──────────────────────────────────────────────────\n");

  return { success: succeeded.length > 0, platforms: results };
}

module.exports = { install, BUNDLES };
