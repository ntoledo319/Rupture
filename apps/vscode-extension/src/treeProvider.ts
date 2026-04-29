import * as vscode from 'vscode';

export class RuptureTreeProvider implements vscode.TreeDataProvider<RuptureTreeItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<RuptureTreeItem | undefined | null | void> = new vscode.EventEmitter<RuptureTreeItem | undefined | null | void>();
    readonly onDidChangeTreeData: vscode.Event<RuptureTreeItem | undefined | null | void> = this._onDidChangeTreeData.event;

    private findings: Finding[] = [];

    refresh(): void {
        this._onDidChangeTreeData.fire();
    }

    updateFindings(findings: Finding[]): void {
        this.findings = findings;
        this.refresh();
    }

    getTreeItem(element: RuptureTreeItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: RuptureTreeItem): Thenable<RuptureTreeItem[]> {
        if (!element) {
            // Root level - group by severity
            const severities = ['critical', 'high', 'medium', 'low'];
            const items: RuptureTreeItem[] = [];

            for (const severity of severities) {
                const count = this.findings.filter(f => f.severity === severity).length;
                if (count > 0) {
                    items.push(new RuptureTreeItem(
                        `${severity.toUpperCase()} (${count})`,
                        severity,
                        vscode.TreeItemCollapsibleState.Collapsed,
                        undefined,
                        severity
                    ));
                }
            }

            if (items.length === 0) {
                items.push(new RuptureTreeItem(
                    'No deprecations found',
                    'info',
                    vscode.TreeItemCollapsibleState.None
                ));
            }

            return Promise.resolve(items);
        } else {
            // Children - show individual findings
            const severity = element.severity;
            const items = this.findings
                .filter(f => f.severity === severity)
                .map(f => new RuptureTreeItem(
                    f.message,
                    'finding',
                    vscode.TreeItemCollapsibleState.None,
                    {
                        command: 'vscode.open',
                        title: 'Open File',
                        arguments: [vscode.Uri.file(f.file), {
                            selection: new vscode.Range(f.line - 1, f.character, f.line - 1, f.character)
                        }]
                    },
                    undefined,
                    f.file
                ));

            return Promise.resolve(items);
        }
    }
}

class RuptureTreeItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly type: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly command?: vscode.Command,
        public readonly severity?: string,
        public readonly tooltip?: string
    ) {
        super(label, collapsibleState);

        this.tooltip = tooltip || label;
        this.description = tooltip ? tooltip.split('/').pop() : '';

        // Set icon based on type/severity
        if (type === 'critical') {
            this.iconPath = new vscode.ThemeIcon('error');
        } else if (type === 'high') {
            this.iconPath = new vscode.ThemeIcon('warning');
        } else if (type === 'medium') {
            this.iconPath = new vscode.ThemeIcon('info');
        } else if (type === 'low') {
            this.iconPath = new vscode.ThemeIcon('info');
        } else if (type === 'finding') {
            this.iconPath = new vscode.ThemeIcon('file-code');
        } else {
            this.iconPath = new vscode.ThemeIcon('check');
        }

        this.contextValue = type;
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
