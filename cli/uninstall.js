/**
 * AgentKit CLI — Uninstaller
 * `npx agentkit uninstall` — removes all AgentKit files from current project.
 * `npx agentkit uninstall --purge` — also deletes runtime data (.agentkit/)
 */

"use strict";

const fs   = require("fs");
const path = require("path");

function uninstall(options = {}) {
  const cwd    = options.cwd    || process.cwd();
  const purge  = options.purge  || false;
  const silent = options.silent || false;

  function log(...args) { if (!silent) console.log(...args); }

  log("\nAgentKit Uninstaller");
  log("─────────────────────────\n");

  const removed  = [];
  const skipped  = [];

  // ── 1. Claude Code ──────────────────────────────────────────────────────────
  // Remove .claude/agentkit/ (installed skill files)
  const claudeSkillsDir = path.join(cwd, ".claude", "agentkit");
  if (fs.existsSync(claudeSkillsDir)) {
    fs.rmSync(claudeSkillsDir, { recursive: true, force: true });
    removed.push(".claude/agentkit/");
  } else {
    skipped.push(".claude/agentkit/");
  }

  // Strip AgentKit hooks from .claude/settings.json (keep user's other hooks)
  const settingsPath = path.join(cwd, ".claude", "settings.json");
  if (fs.existsSync(settingsPath)) {
    try {
      const settings = JSON.parse(fs.readFileSync(settingsPath, "utf8"));
      const cleaned  = _stripAgentKitHooks(settings);
      // If hooks object is now empty, remove the key entirely
      if (cleaned.hooks && Object.keys(cleaned.hooks).length === 0) {
        delete cleaned.hooks;
      }
      fs.writeFileSync(settingsPath, JSON.stringify(cleaned, null, 2));
      removed.push(".claude/settings.json  (hooks removed, file kept)");
    } catch (e) {
      skipped.push(`.claude/settings.json  (parse error: ${e.message})`);
    }
  } else {
    skipped.push(".claude/settings.json");
  }

  // Remove .agentkit.yaml
  const yamlPath = path.join(cwd, ".agentkit.yaml");
  if (fs.existsSync(yamlPath)) {
    fs.unlinkSync(yamlPath);
    removed.push(".agentkit.yaml");
  }

  // ── 2. Cursor ────────────────────────────────────────────────────────────────
  const cursorRulesDir = path.join(cwd, ".cursor", "rules");
  if (fs.existsSync(cursorRulesDir)) {
    const mdcFiles = fs.readdirSync(cursorRulesDir)
      .filter(f => f.startsWith("agentkit-") && f.endsWith(".mdc"));
    for (const f of mdcFiles) {
      fs.unlinkSync(path.join(cursorRulesDir, f));
    }
    if (mdcFiles.length > 0) {
      removed.push(`.cursor/rules/agentkit-*.mdc  (${mdcFiles.length} files)`);
    } else {
      skipped.push(".cursor/rules/agentkit-*.mdc");
    }
  }

  // ── 3. Gemini CLI ────────────────────────────────────────────────────────────
  for (const f of ["GEMINI.md", "config.yaml"]) {
    const p = path.join(cwd, ".gemini", f);
    if (fs.existsSync(p)) {
      fs.unlinkSync(p);
      removed.push(`.gemini/${f}`);
    }
  }
  // Remove .gemini/ dir if now empty
  const geminiDir = path.join(cwd, ".gemini");
  if (fs.existsSync(geminiDir) && fs.readdirSync(geminiDir).length === 0) {
    fs.rmdirSync(geminiDir);
  }

  // ── 4. OpenCode ──────────────────────────────────────────────────────────────
  const opencodeConfig = path.join(cwd, ".opencode", "config.json");
  if (fs.existsSync(opencodeConfig)) {
    fs.unlinkSync(opencodeConfig);
    removed.push(".opencode/config.json");
    const opencodeDir = path.join(cwd, ".opencode");
    if (fs.readdirSync(opencodeDir).length === 0) fs.rmdirSync(opencodeDir);
  }

  // ── 5. Windsurf ──────────────────────────────────────────────────────────────
  const windsurfRules = path.join(cwd, ".windsurf", "rules.md");
  if (fs.existsSync(windsurfRules)) {
    fs.unlinkSync(windsurfRules);
    removed.push(".windsurf/rules.md");
    const windsurfDir = path.join(cwd, ".windsurf");
    if (fs.readdirSync(windsurfDir).length === 0) fs.rmdirSync(windsurfDir);
  }

  // ── 6. Kilo Code ─────────────────────────────────────────────────────────────
  const kiloDir = path.join(cwd, ".kilo", "plugins");
  if (fs.existsSync(kiloDir)) {
    const kiloFiles = fs.readdirSync(kiloDir)
      .filter(f => f.startsWith("agentkit-") && f.endsWith(".yaml"));
    for (const f of kiloFiles) {
      fs.unlinkSync(path.join(kiloDir, f));
    }
    if (kiloFiles.length > 0) {
      removed.push(`.kilo/plugins/agentkit-*.yaml  (${kiloFiles.length} files)`);
    }
  }

  // ── 7. Aider ─────────────────────────────────────────────────────────────────
  const aiderConf = path.join(cwd, ".aider.conf.yml");
  if (fs.existsSync(aiderConf)) {
    const content = fs.readFileSync(aiderConf, "utf8");
    if (content.includes("# AgentKit")) {
      const stripped = _stripSection(content, "# AgentKit", "# END AgentKit");
      if (stripped.trim()) {
        fs.writeFileSync(aiderConf, stripped);
        removed.push(".aider.conf.yml  (AgentKit section removed, file kept)");
      } else {
        fs.unlinkSync(aiderConf);
        removed.push(".aider.conf.yml");
      }
    }
  }

  // ── 8. Augment ───────────────────────────────────────────────────────────────
  const augmentCtx = path.join(cwd, ".augment", "context.md");
  if (fs.existsSync(augmentCtx)) {
    fs.unlinkSync(augmentCtx);
    removed.push(".augment/context.md");
    const augmentDir = path.join(cwd, ".augment");
    if (fs.readdirSync(augmentDir).length === 0) fs.rmdirSync(augmentDir);
  }

  // ── 9. Codex (AGENTS.md) ─────────────────────────────────────────────────────
  const agentsMd = path.join(cwd, "AGENTS.md");
  if (fs.existsSync(agentsMd)) {
    const content = fs.readFileSync(agentsMd, "utf8");
    if (content.includes("<!-- AGENTKIT_SKILLS_START -->")) {
      const stripped = _stripSection(
        content,
        "<!-- AGENTKIT_SKILLS_START -->",
        "<!-- AGENTKIT_SKILLS_END -->",
      );
      if (stripped.trim()) {
        fs.writeFileSync(agentsMd, stripped);
        removed.push("AGENTS.md  (AgentKit section removed, file kept)");
      } else {
        fs.unlinkSync(agentsMd);
        removed.push("AGENTS.md");
      }
    }
  }

  // ── 10. Runtime data (only with --purge) ─────────────────────────────────────
  const runtimeDir = path.join(cwd, ".agentkit");
  if (purge && fs.existsSync(runtimeDir)) {
    fs.rmSync(runtimeDir, { recursive: true, force: true });
    removed.push(".agentkit/  (runtime data — costs, memory, workflow state)");
  } else if (!purge && fs.existsSync(runtimeDir)) {
    log("  ℹ  Runtime data kept (.agentkit/) — re-run with --purge to delete costs/memory/state\n");
  }

  // ── Summary ───────────────────────────────────────────────────────────────────
  if (removed.length > 0) {
    log("Removed:");
    for (const f of removed) log(`  ✓ ${f}`);
  }
  if (skipped.length > 0 && options.verbose) {
    log("\nNot found (skipped):");
    for (const f of skipped) log(`  ○ ${f}`);
  }

  log("\n✓ AgentKit uninstalled from this project.");
  log("  To reinstall: npx agentkit init\n");

  return { success: true, removed, skipped };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Remove all hooks from settings.json whose command contains an agentkit path. */
function _stripAgentKitHooks(settings) {
  if (!settings.hooks) return settings;

  const AGENTKIT_MARKERS = [
    "skill_router_hook",
    "session_start.sh",
    "session_end.sh",
    "memory_inject.sh",
    "memory_recorder.sh",
    "model_router_hook.sh",
    "thinking_budget.sh",
    "workflow_state.sh",
    "plan_gate.sh",
    "research_gate.sh",
    "quality_gates.sh",
    "cost_dashboard.sh",
    "forced_eval.sh",
    "agentkit",
  ];

  for (const [event, buckets] of Object.entries(settings.hooks)) {
    if (!Array.isArray(buckets)) continue;
    settings.hooks[event] = buckets
      .map(bucket => {
        if (!bucket.hooks) return bucket;
        bucket.hooks = bucket.hooks.filter(h => {
          const cmd = h.command || "";
          return !AGENTKIT_MARKERS.some(m => cmd.includes(m));
        });
        return bucket;
      })
      .filter(bucket => bucket.hooks && bucket.hooks.length > 0);
  }

  return settings;
}

/** Remove a delimited section from a text file. */
function _stripSection(text, startMarker, endMarker) {
  const startIdx = text.indexOf(startMarker);
  const endIdx   = text.indexOf(endMarker);
  if (startIdx === -1) return text;
  const end = endIdx === -1 ? text.length : endIdx + endMarker.length;
  return text.slice(0, startIdx) + text.slice(end);
}

module.exports = { uninstall };
