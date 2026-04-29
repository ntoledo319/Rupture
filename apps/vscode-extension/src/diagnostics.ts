import * as vscode from 'vscode';

export class RuptureDiagnostics {
    private diagnosticCollection: vscode.DiagnosticCollection;
    private allFindings: Map<string, Finding[]> = new Map();

    constructor() {
        this.diagnosticCollection = vscode.languages.createDiagnosticCollection('rupture');
    }

    setFindings(uri: vscode.Uri, findings: Finding[]): void {
        this.allFindings.set(uri.toString(), findings);

        const diagnostics: vscode.Diagnostic[] = findings.map(f => {
            const range = new vscode.Range(
                new vscode.Position(f.line - 1, f.character),
                new vscode.Position(f.line - 1, f.character + 10)
            );

            const diagnostic = new vscode.Diagnostic(
                range,
                f.message,
                this.severityToDiagnostic(f.severity)
            );
            diagnostic.code = f.code;
            diagnostic.source = 'Rupture';

            return diagnostic;
        });

        this.diagnosticCollection.set(uri, diagnostics);
    }

    getAllFindings(): Finding[] {
        const result: Finding[] = [];
        for (const [uri, findings] of this.allFindings) {
            result.push(...findings);
        }
        return result.sort((a, b) => this.severityRank(b.severity) - this.severityRank(a.severity));
    }

    clear(): void {
        this.diagnosticCollection.clear();
        this.allFindings.clear();
    }

    private severityToDiagnostic(severity: string): vscode.DiagnosticSeverity {
        switch (severity) {
            case 'critical':
            case 'high':
                return vscode.DiagnosticSeverity.Error;
            case 'medium':
                return vscode.DiagnosticSeverity.Warning;
            case 'low':
            default:
                return vscode.DiagnosticSeverity.Information;
        }
    }

    private severityRank(severity: string): number {
        const ranks: Record<string, number> = {
            critical: 4,
            high: 3,
            medium: 2,
            low: 1
        };
        return ranks[severity] || 0;
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
