import * as vscode from 'vscode';
import { EOLkitsScanner } from './scanner';
import { EOLkitsDiagnostics } from './diagnostics';
import { EOLkitsTreeProvider } from './treeProvider';

let scanner: EOLkitsScanner;
let diagnostics: EOLkitsDiagnostics;
let treeProvider: EOLkitsTreeProvider;

export function activate(context: vscode.ExtensionContext) {
    console.log('EOLkits extension activated');

    // Initialize components
    diagnostics = new EOLkitsDiagnostics();
    scanner = new EOLkitsScanner(diagnostics);
    treeProvider = new EOLkitsTreeProvider();

    // Register tree view
    vscode.window.registerTreeDataProvider('eolkits.deprecations', treeProvider);

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('eolkits.scanWorkspace', () => {
            scanWorkspace();
        }),
        vscode.commands.registerCommand('eolkits.showReport', () => {
            showReport();
        }),
        vscode.commands.registerCommand('eolkits.getAudit', () => {
            vscode.env.openExternal(vscode.Uri.parse('https://eolkits.com/audit/?utm_source=vscode&utm_medium=extension&source=vscode'));
        })
    );

    // Auto-scan on save
    vscode.workspace.onDidSaveTextDocument((document) => {
        const config = vscode.workspace.getConfiguration('eolkits');
        if (config.get<boolean>('autoScan', true)) {
            scanner.scanDocument(document);
        }
    });

    // Initial workspace scan
    scanWorkspace();
}

async function scanWorkspace() {
    const progressOptions = {
        location: vscode.ProgressLocation.Window,
        title: 'EOLkits: Scanning for AWS deprecations...'
    };

    await vscode.window.withProgress(progressOptions, async (progress) => {
        const files = await vscode.workspace.findFiles(
            '**/*.{yaml,yml,json,tf,js,ts,py}',
            '**/node_modules/**'
        );

        progress.report({ increment: 0 });

        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            try {
                const document = await vscode.workspace.openTextDocument(file);
                await scanner.scanDocument(document);
            } catch (e) {
                // Skip files that can't be opened
            }
            progress.report({ increment: (i / files.length) * 100 });
        }

        // Update tree view
        const findings = diagnostics.getAllFindings();
        treeProvider.updateFindings(findings);

        // Show summary
        const count = findings.length;
        if (count > 0) {
            vscode.window.showWarningMessage(
                `EOLkits found ${count} potential deprecation issue${count === 1 ? '' : 's'}.`,
                'View Report'
            ).then(selection => {
                if (selection === 'View Report') {
                    showReport();
                }
            });
        } else {
            vscode.window.showInformationMessage('EOLkits: No deprecation issues found.');
        }
    });
}

function showReport() {
    const findings = diagnostics.getAllFindings();

    const panel = vscode.window.createWebviewPanel(
        'eolkitsReport',
        'EOLkits Deprecation Report',
        vscode.ViewColumn.One,
        {}
    );

    panel.webview.html = generateReportHtml(findings);
}

function generateReportHtml(findings: any[]): string {
    const rows = findings.map(f => `
        <tr>
            <td><span class="severity ${f.severity}">${f.severity}</span></td>
            <td>${f.message}</td>
            <td>${f.file}</td>
            <td>Line ${f.line}</td>
        </tr>
    `).join('');

    return `<!DOCTYPE html>
    <html>
    <head>
        <style>
            body { font-family: sans-serif; padding: 20px; }
            table { width: 100%; border-collapse: collapse; }
            th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background: #f5f5f5; }
            .severity { padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
            .critical { background: #fee; color: #c00; }
            .high { background: #ffe8cc; color: #c60; }
            .medium { background: #ffffcc; color: #880; }
            .low { background: #efe; color: #080; }
        </style>
    </head>
    <body>
        <h1>EOLkits Deprecation Report</h1>
        <p>Found ${findings.length} issue(s)</p>
        <table>
            <tr>
                <th>Severity</th>
                <th>Issue</th>
                <th>File</th>
                <th>Location</th>
            </tr>
            ${rows}
        </table>
        <p><a href="https://eolkits.com/audit/?utm_source=vscode&utm_medium=extension&source=vscode">Get full audit report →</a></p>
    </body>
    </html>`;
}

export function deactivate() {
    console.log('EOLkits extension deactivated');
}
