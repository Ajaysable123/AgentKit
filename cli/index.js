#!/usr/bin/env node
/**
 * AgentKit CLI — Main Entry Point
 * Usage: npx agentkit <command> [options]
 *
 * Commands:
 *   init              Detect platforms and install AgentKit
 *   uninstall         Remove all AgentKit files from current project
 *   sync              Re-sync config across all detected platforms
 *   status            Show health check + installed platforms + costs
 *   costs [--days N]  Show cost analytics report
 *   skills list       List installed skills
 *   skills info <id>  Show details for a skill
 *   workflow status   Show current workflow state
 *   workflow approve  Approve the current plan
 *   workflow reset    Reset workflow to IDLE
 *   detect            Show detected platforms only
 */

"use strict";

const path = require("path");

const { detectPlatforms }  = require("./detect-platform");
const { install, BUNDLES } = require("./install");
const { sync }             = require("./sync");
const { status }           = require("./status");
const { costs }            = require("./costs");
const { listSkills, skillInfo } = require("./skills");
const { uninstall } = require("./uninstall");

// Package root: where skills/, hooks/, router/, etc. live (the npm install dir)
const AGENTKIT_HOME = process.env.AGENTKIT_HOME
  || path.join(__dirname, "..");

// ---------------------------------------------------------------------------
// Argument parsing (no external deps — works via npx without install)
// ---------------------------------------------------------------------------

const args  = process.argv.slice(2);
const cmd   = args[0] || "help";
const sub   = args[1];
const flags = parseFlags(args.slice(1));

function parseFlags(argv) {
  const result = {};
  for (let i = 0; i < argv.length; i++) {
    if (argv[i].startsWith("--")) {
      const key = argv[i].slice(2);
      result[key] = argv[i + 1] && !argv[i + 1].startsWith("--")
        ? argv[++i]
        : true;
    }
  }
  return result;
}

// ---------------------------------------------------------------------------
// Dispatch
// ---------------------------------------------------------------------------

switch (cmd) {
  case "uninstall":
    uninstall({
      cwd:    process.cwd(),
      purge:  flags.purge || false,
      verbose: flags.verbose || false,
    });
    break;

  case "init":
    install({
      agentKitHome: AGENTKIT_HOME,
      bundle:       flags.bundle || "backend-pro",
      platforms:    flags.platform ? [flags.platform] : undefined,
    });
    break;

  case "sync":
    sync({
      agentKitHome: AGENTKIT_HOME,
      bundle:       flags.bundle || "backend-pro",
    });
    break;

  case "status":
    status({ agentKitHome: AGENTKIT_HOME });
    break;

  case "costs":
    costs({
      agentKitHome: AGENTKIT_HOME,
      days:         parseInt(flags.days || "7", 10),
    });
    break;

  case "skills":
    if (sub === "list" || !sub) {
      listSkills({ agentKitHome: AGENTKIT_HOME });
    } else if (sub === "info" && args[2]) {
      skillInfo(args[2], { agentKitHome: AGENTKIT_HOME });
    } else {
      console.log("Usage: agentkit skills list | skills info <id>");
    }
    break;

  case "workflow": {
    const { spawnSync } = require("child_process");
    const wcmd = sub || "status";
    const result = spawnSync(
      "python3",
      [path.join(AGENTKIT_HOME, "workflow", "enforcer.py"), wcmd],
      { stdio: "inherit", cwd: process.cwd() },
    );
    process.exit(result.status || 0);
    break;
  }

  case "detect":
    console.log("\nDetected platforms:");
    for (const p of detectPlatforms()) {
      const tier = ["", "Full", "Partial", "Basic"][p.tier] || "?";
      console.log(`  ✓ ${p.name.padEnd(20)} Tier ${p.tier} (${tier})`);
    }
    console.log("");
    break;

  case "bundles":
    console.log("\nAvailable skill bundles:");
    for (const [key, bundle] of Object.entries(BUNDLES)) {
      console.log(`  ${key.padEnd(20)} ${bundle.name} (${bundle.skills.length} skills)`);
    }
    console.log("");
    break;

  case "help":
  default:
    printHelp();
    break;
}

function printHelp() {
  console.log(`
AgentKit v0.5.4 — Intelligent orchestration for agentic coding

Usage: npx agentkit <command> [options]

Commands:
  init              Detect platforms and install AgentKit
  uninstall         Remove all AgentKit files from current project
  sync              Re-sync config across all detected platforms
  status            Health check + installed platforms + costs
  costs             Cost analytics (--days N, default 7)
  skills list       List all installed skills
  skills info <id>  Show details for a skill
  workflow status   Show current workflow state
  workflow approve  Approve the current implementation plan
  workflow reset    Reset workflow to IDLE (start fresh)
  detect            Show detected AI coding platforms
  bundles           List available skill bundles

Options:
  --bundle <name>   Skill bundle for init/sync (default: backend-pro)
  --platform <id>   Install for a specific platform only
  --days <N>        Days for cost report (default: 7)
  --purge           uninstall: also delete runtime data (.agentkit/ costs/memory/state)

Environment:
  AGENTKIT_HOME     Override package root (default: npm install directory)
  AGENTKIT_PROJECT  Project root for workflow state (default: cwd)
`);
}
