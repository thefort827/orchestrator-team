#!/usr/bin/env node
/**
 * orchestrator-team CLI
 * Usage: npx orchestrator-team <command>
 */

const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const args = process.argv.slice(2);
const command = args[0];

const PY_CORE = path.join(__dirname, '..', 'orchestrator_team');

function run(cmd) {
    try {
        execSync(cmd, { stdio: 'inherit', cwd: path.join(__dirname, '..') });
    } catch (e) {
        process.exit(e.status || 1);
    }
}

const help = `
orchestrator-team — Multi-Agent Orchestration Framework

Usage:
  orchestrator-team <command>

Commands:
  init        Initialize a new orchestration project
  run         Run a workflow from YAML
  validate    Validate a workflow file
  benchmark   Run benchmark tests
  version     Show version
  help        Show this help

Examples:
  npx orchestrator-team init my-project
  npx orchestrator-team run workflow.yaml
  npx orchestrator-team validate workflow.yaml
  pip install orchestrator-team
`;

switch (command) {
    case 'init':
        const name = args[1] || 'my-project';
        console.log(`Initializing project: ${name}`);
        run(`python -c "from orchestrator_team.scaffold import init_project; init_project('${name}')"`);
        break;
    case 'run':
        const workflow = args[1] || 'workflow.yaml';
        console.log(`Running workflow: ${workflow}`);
        run(`python -m orchestrator_team.run ${workflow}`);
        break;
    case 'validate':
        const wf = args[1] || 'workflow.yaml';
        console.log(`Validating: ${wf}`);
        run(`python -m orchestrator_team.validate ${wf}`);
        break;
    case 'benchmark':
        run(`python -m orchestrator_team.benchmark`);
        break;
    case 'version':
        const pkg = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'package.json'), 'utf8'));
        console.log(`orchestrator-team v${pkg.version}`);
        break;
    case 'help':
    case '--help':
    case '-h':
    case undefined:
        console.log(help);
        break;
    default:
        console.error(`Unknown command: ${command}`);
        console.log(help);
        process.exit(1);
}
