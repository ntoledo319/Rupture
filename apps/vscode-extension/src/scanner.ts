import * as vscode from 'vscode';
import { RuptureDiagnostics } from './diagnostics';

export class RuptureScanner {
    constructor(private diagnostics: RuptureDiagnostics) {}

    async scanDocument(document: vscode.TextDocument): Promise<void> {
        const text = document.getText();
        const findings: Finding[] = [];

        // Check file type and run appropriate scan
        if (document.languageId === 'yaml' || document.languageId === 'json') {
            findings.push(...this.scanCloudFormation(text, document));
        }

        if (document.languageId === 'javascript' || document.languageId === 'typescript') {
            findings.push(...this.scanJavaScript(text, document));
        }

        if (document.languageId === 'python') {
            findings.push(...this.scanPython(text, document));
        }

        if (document.fileName.endsWith('.tf') || document.fileName.endsWith('.hcl')) {
            findings.push(...this.scanTerraform(text, document));
        }

        // Update diagnostics for this document
        this.diagnostics.setFindings(document.uri, findings);
    }

    private scanCloudFormation(text: string, document: vscode.TextDocument): Finding[] {
        const findings: Finding[] = [];
        const lines = text.split('\n');

        // Check for Lambda Node.js 20
        const node20Pattern = /Runtime:\s*nodejs20\.x/g;
        let match;
        while ((match = node20Pattern.exec(text)) !== null) {
            const line = text.substring(0, match.index).split('\n').length - 1;
            findings.push({
                severity: 'critical',
                message: 'Lambda Node.js 20 runtime deprecated (EOL: 2026-04-30)',
                file: document.fileName,
                line: line + 1,
                character: match.index - text.lastIndexOf('\n', match.index) - 1,
                code: 'LAMBDA_NODE20_EOL'
            });
        }

        // Check for Python 3.9-3.11
        const pythonPattern = /Runtime:\s*python3\.(9|10|11)/g;
        while ((match = pythonPattern.exec(text)) !== null) {
            const line = text.substring(0, match.index).split('\n').length - 1;
            const version = match[1];
            const eolDates: Record<string, string> = {
                '9': '2026-10-31',
                '10': '2027-04-30',
                '11': '2027-10-31'
            };
            findings.push({
                severity: version === '9' ? 'high' : 'medium',
                message: `Lambda Python 3.${version} deprecated (EOL: ${eolDates[version]})`,
                file: document.fileName,
                line: line + 1,
                character: match.index - text.lastIndexOf('\n', match.index) - 1,
                code: `LAMBDA_PYTHON3${version}_EOL`
            });
        }

        // Check for Amazon Linux 2
        const al2Pattern = /ImageId.*amazonlinux2|AMI.*AL2/gi;
        while ((match = al2Pattern.exec(text)) !== null) {
            const line = text.substring(0, match.index).split('\n').length - 1;
            findings.push({
                severity: 'high',
                message: 'Amazon Linux 2 deprecated (EOL: 2026-06-30)',
                file: document.fileName,
                line: line + 1,
                character: match.index - text.lastIndexOf('\n', match.index) - 1,
                code: 'AMAZON_LINUX2_EOL'
            });
        }

        return findings;
    }

    private scanJavaScript(text: string, document: vscode.TextDocument): Finding[] {
        const findings: Finding[] = [];

        // Check for aws-sdk v2 imports
        const sdkV2Pattern = /require\(['"]aws-sdk['"]\)|from ['"]aws-sdk['"]/g;
        let match;
        while ((match = sdkV2Pattern.exec(text)) !== null) {
            const line = text.substring(0, match.index).split('\n').length - 1;
            findings.push({
                severity: 'medium',
                message: 'aws-sdk v2 deprecated in Lambda Node.js 22, migrate to v3',
                file: document.fileName,
                line: line + 1,
                character: match.index - text.lastIndexOf('\n', match.index) - 1,
                code: 'AWS_SDK_V2_DEPRECATED'
            });
        }

        return findings;
    }

    private scanPython(text: string, document: vscode.TextDocument): Finding[] {
        const findings: Finding[] = [];

        // Check for deprecated modules
        const deprecatedPatterns = [
            { pattern: /from distutils/g, message: 'distutils deprecated, use setuptools', severity: 'medium' },
            { pattern: /import imp\b/g, message: 'imp module deprecated, use importlib', severity: 'medium' },
            { pattern: /from collections import.*Mapping/g, message: 'collections.Mapping deprecated, use collections.abc.Mapping', severity: 'low' },
        ];

        for (const { pattern, message, severity } of deprecatedPatterns) {
            let match;
            while ((match = pattern.exec(text)) !== null) {
                const line = text.substring(0, match.index).split('\n').length - 1;
                findings.push({
                    severity: severity as any,
                    message,
                    file: document.fileName,
                    line: line + 1,
                    character: match.index - text.lastIndexOf('\n', match.index) - 1,
                    code: 'PYTHON_DEPRECATED_MODULE'
                });
            }
        }

        return findings;
    }

    private scanTerraform(text: string, document: vscode.TextDocument): Finding[] {
        const findings: Finding[] = [];

        // Check for deprecated AMIs in launch templates
        const amiPattern = /ami.*amazon-linux-2|al2-ami/gi;
        let match;
        while ((match = amiPattern.exec(text)) !== null) {
            const line = text.substring(0, match.index).split('\n').length - 1;
            findings.push({
                severity: 'high',
                message: 'Amazon Linux 2 AMI deprecated (EOL: 2026-06-30)',
                file: document.fileName,
                line: line + 1,
                character: match.index - text.lastIndexOf('\n', match.index) - 1,
                code: 'TF_AL2_AMI_DEPRECATED'
            });
        }

        return findings;
    }
}

interface Finding {
    severity: 'critical' | 'high' | 'medium' | 'low';
    message: string;
    file: string;
    line: number;
    character: number;
    code: string;
}
