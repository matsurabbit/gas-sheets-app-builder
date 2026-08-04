#!/usr/bin/env node

import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { join } from 'node:path';
import { spawn } from 'node:child_process';
import { pathToFileURL } from 'node:url';

const SHEET_MIME_TYPE = 'application/vnd.google-apps.spreadsheet';
const ID_PATTERN = /^[A-Za-z0-9_-]{20,}$/;

function parseArgs(values) {
  const result = { user: 'default', dryRun: false };
  for (let index = 0; index < values.length; index += 1) {
    const value = values[index];
    if (value === '--dry-run') {
      result.dryRun = true;
    } else if (['--folder-id', '--title', '--auth', '--user'].includes(value)) {
      const next = values[index + 1];
      if (!next) throw new Error(`${value} requires a value`);
      result[value.slice(2).replace('-id', 'Id')] = next;
      index += 1;
    } else {
      throw new Error(`Unknown option: ${value}`);
    }
  }
  if (!result.folderId || !ID_PATTERN.test(result.folderId)) {
    throw new Error('--folder-id must be a Google Drive folder ID');
  }
  if (!result.title || !result.title.trim()) {
    throw new Error('--title is required');
  }
  return result;
}

function runNode(args, cwd) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, args, { cwd, stdio: 'inherit' });
    child.on('error', reject);
    child.on('exit', code => {
      if (code === 0) resolve();
      else reject(new Error(`clasp exited with code ${code}`));
    });
  });
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const projectRoot = process.cwd();
  const claspRoot = join(projectRoot, 'node_modules', '@google', 'clasp');
  const claspEntry = join(claspRoot, 'build', 'src', 'index.js');
  const authModulePath = join(claspRoot, 'build', 'src', 'auth', 'auth.js');
  const claspConfigPath = join(projectRoot, '.clasp.json');

  if (!existsSync(claspEntry) || !existsSync(authModulePath)) {
    throw new Error('Local @google/clasp was not found. Run npm install first.');
  }
  const driveRequest = {
    name: args.title.trim(),
    mimeType: SHEET_MIME_TYPE,
    parents: [args.folderId],
  };
  const claspArgs = [claspEntry];
  if (args.auth) claspArgs.push('--auth', args.auth);
  claspArgs.push('--user', args.user, 'create-script', '--title', args.title.trim(), '--parentId', '<CREATED_SHEET_ID>');

  if (args.dryRun) {
    console.log(JSON.stringify({ dryRun: true, driveRequest, claspArgs }, null, 2));
    return;
  }

  if (existsSync(claspConfigPath)) {
    throw new Error('.clasp.json already exists. Refusing to create a duplicate project.');
  }

  const { initAuth } = await import(pathToFileURL(authModulePath).href);
  const auth = await initAuth({ authFilePath: args.auth, userKey: args.user });
  if (!auth.credentials) {
    throw new Error('clasp is not logged in. Complete clasp login and retry.');
  }

  const requireFromClasp = createRequire(join(claspRoot, 'package.json'));
  const { google } = requireFromClasp('googleapis');
  const drive = google.drive({ version: 'v3', auth: auth.credentials });
  const created = await drive.files.create({
    requestBody: driveRequest,
    supportsAllDrives: true,
    fields: 'id,name,mimeType,parents,webViewLink',
  });

  const sheet = created.data;
  if (!sheet.id) throw new Error('Drive API did not return a Sheet ID.');
  if (sheet.mimeType !== SHEET_MIME_TYPE) {
    throw new Error(`Unexpected MIME type for created file ${sheet.id}: ${sheet.mimeType}`);
  }
  if (!Array.isArray(sheet.parents) || sheet.parents.length !== 1 || sheet.parents[0] !== args.folderId) {
    throw new Error(`Sheet ${sheet.id} was not created directly in the requested folder. Binding was not attempted.`);
  }

  claspArgs[claspArgs.length - 1] = sheet.id;
  try {
    await runNode(claspArgs, projectRoot);
  } catch (error) {
    throw new Error(`Sheet ${sheet.id} was created in the requested folder, but Script binding failed: ${error.message}`);
  }

  const claspConfig = JSON.parse(await readFile(claspConfigPath, 'utf8'));
  if (claspConfig.parentId !== sheet.id || !claspConfig.scriptId) {
    throw new Error('Created .clasp.json does not match the directly created Sheet.');
  }

  console.log(JSON.stringify({
    title: sheet.name,
    spreadsheetId: sheet.id,
    spreadsheetUrl: sheet.webViewLink || `https://docs.google.com/spreadsheets/d/${sheet.id}/edit`,
    folderId: args.folderId,
    scriptId: claspConfig.scriptId,
    createdDirectlyInFolder: true,
  }, null, 2));
}

main().catch(error => {
  console.error(error.message);
  process.exitCode = 1;
});
