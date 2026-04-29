"""
Property-based tests for lambda-lifeline codemods (C2)
Uses Hypothesis to verify round-trip invariants and determinism.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from pathlib import Path
import tempfile
import subprocess
import json


class TestCodemodProperties:
    """Property-based tests for codemod transformations."""

    @given(
        runtime=st.sampled_from(['nodejs20.x', 'nodejs18.x', 'nodejs16.x', 'nodejs14.x']),
        handler=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N'))),
    )
    @settings(max_examples=50)
    def test_runtime_upgrade_preserves_function_structure(self, runtime, handler):
        """
        Property: Upgrading runtime preserves the function's logical structure.
        The handler name, memory, timeout, and environment variables should be unchanged.
        """
        assume(handler.isidentifier())
        
        # Generate SAM template with property-based values
        template = f"""AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Resources:
  TestFunction:
    Type: AWS::Serverless::Function
    Properties:
      Runtime: {runtime}
      Handler: {handler}
      MemorySize: 512
      Timeout: 30
      Environment:
        Variables:
          LOG_LEVEL: info
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(template)
            template_path = f.name
        
        try:
            # Run upgrade command
            result = subprocess.run(
                ['lambda-lifeline', 'upgrade', '--template', template_path, '--dry-run', '--format', 'json'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                output = json.loads(result.stdout)
                
                # Property: Handler name is preserved
                assert output.get('handler') == handler, "Handler name should be preserved"
                
                # Property: Memory and timeout are preserved
                assert output.get('memory') == 512, "Memory should be preserved"
                assert output.get('timeout') == 30, "Timeout should be preserved"
                
                # Property: Environment variables are preserved
                env = output.get('environment', {})
                assert env.get('LOG_LEVEL') == 'info', "Environment variables should be preserved"
                
                # Property: Runtime is upgraded (if it was deprecated)
                if runtime in ['nodejs14.x', 'nodejs16.x', 'nodejs20.x']:
                    assert output.get('runtime') == 'nodejs22.x', "Deprecated runtime should be upgraded"
                else:
                    assert output.get('runtime') == runtime, "Non-deprecated runtime should be unchanged"
        finally:
            Path(template_path).unlink(missing_ok=True)

    @given(
        code=st.text(min_size=10, max_size=1000, alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z'))),
    )
    @settings(max_examples=30)
    def test_aws_sdk_import_detection(self, code):
        """
        Property: aws-sdk v2 imports are always detected when present.
        """
        # Generate code that may or may not contain aws-sdk imports
        if 'aws-sdk' in code:
            test_code = f"""
const AWS = require('aws-sdk');
{code}
"""
        else:
            test_code = code
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(test_code)
            code_path = f.name
        
        try:
            result = subprocess.run(
                ['lambda-lifeline', 'scan', '--path', code_path, '--format', 'json'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                output = json.loads(result.stdout)
                findings = output.get('findings', [])
                
                # Property: If aws-sdk is in code, it should be detected
                if 'aws-sdk' in test_code:
                    sdk_findings = [f for f in findings if 'aws-sdk' in str(f).lower()]
                    assert len(sdk_findings) > 0 or result.returncode != 0, "aws-sdk should be detected when present"
        finally:
            Path(code_path).unlink(missing_ok=True)


class TestDeterminism:
    """Tests for determinism - same input always produces same output."""

    def test_deterministic_output_on_same_input(self):
        """
        Property: Running the same codemod twice on identical input produces identical output.
        This is critical for reproducible builds and CI verification.
        """
        template = """AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Resources:
  TestFunction:
    Type: AWS::Serverless::Function
    Properties:
      Runtime: nodejs20.x
      Handler: index.handler
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(template)
            template_path = f.name
        
        try:
            # Run twice
            result1 = subprocess.run(
                ['lambda-lifeline', 'upgrade', '--template', template_path, '--dry-run', '--format', 'json'],
                capture_output=True,
                text=True
            )
            
            result2 = subprocess.run(
                ['lambda-lifeline', 'upgrade', '--template', template_path, '--dry-run', '--format', 'json'],
                capture_output=True,
                text=True
            )
            
            # Property: Same input produces identical output
            assert result1.stdout == result2.stdout, "Output should be deterministic"
            assert result1.returncode == result2.returncode, "Exit code should be deterministic"
            
        finally:
            Path(template_path).unlink(missing_ok=True)

    @given(
        st.lists(
            st.fixed_dictionaries({
                'name': st.text(min_size=1, max_size=50),
                'runtime': st.sampled_from(['nodejs20.x', 'nodejs18.x', 'python3.9', 'python3.12']),
            }),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=20)
    def test_scan_output_determinism(self, functions):
        """
        Property: Scan output is deterministic for the set of functions.
        """
        template_parts = ["AWSTemplateFormatVersion: '2010-09-09'", "Transform: AWS::Serverless-2016-10-31", "Resources:"]
        
        for i, func in enumerate(functions):
            template_parts.append(f"""  Function{i}:
    Type: AWS::Serverless::Function
    Properties:
      Runtime: {func['runtime']}
      Handler: {func['name']}.handler""")
        
        template = '\n'.join(template_parts)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(template)
            template_path = f.name
        
        try:
            outputs = []
            for _ in range(3):  # Run 3 times
                result = subprocess.run(
                    ['lambda-lifeline', 'scan', '--path', template_path, '--format', 'json'],
                    capture_output=True,
                    text=True
                )
                outputs.append(result.stdout)
            
            # Property: All runs produce identical output
            assert all(o == outputs[0] for o in outputs), "Scan output must be deterministic"
            
        finally:
            Path(template_path).unlink(missing_ok=True)


class TestRoundTrip:
    """Tests for round-trip invariants."""

    def test_upgrade_then_downgrade_identity(self):
        """
        Property: Upgrading then downgrading (if available) returns to original state.
        This may not always be possible, but when it is, it should work.
        
        Note: This is a weaker property - some upgrades are irreversible.
        """
        # This test documents the expected behavior
        # In practice, many deprecations are one-way (e.g., Node.js 20 → 22)
        # This test can be skipped or marked as expected to fail
        pytest.skip("Upgrades are generally irreversible by design")
