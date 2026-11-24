/** Replay exported n8n Code nodes locally for independent, credential-free QA.
 * This runner is intentionally limited to this repository's trusted synthetic demo.
 * Never run arbitrary uploaded n8n workflows through new Function().
 */
const fs = require('node:fs');
const path = require('node:path');
const wf = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'workflows', 'n8n-import-demo.json'), 'utf8'));
if (wf.nodes.length !== 10 || wf.nodes.some(n => n.credentials || n.type === 'n8n-nodes-base.httpRequest')) {
  throw new Error('Unexpected external credential or network node in demo');
}
let items = [{json:{}}];
const named = wf.nodes.map(n => n.name);
for (const node of wf.nodes) {
  if (node.type === 'n8n-nodes-base.manualTrigger') continue;
  if (node.type !== 'n8n-nodes-base.code') throw new Error('Unexpected node type');
  const execute = new Function('$input', node.parameters.jsCode);
  const output = execute({first: () => items[0], all: () => items});
  if (!Array.isArray(output) || output.some(item => !item.json)) throw new Error('Invalid n8n Code output: ' + node.name);
  items = output;
}
const result = items[0].json;
if (result.status !== 'DEMO_COMPLETE' || result.sheets_readback.readback_verified !== true) throw new Error('End-to-end QA did not pass');
console.log(JSON.stringify(result, null, 2));
