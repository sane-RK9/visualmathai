import subprocess
import tempfile
import os
from pathlib import Path

class SafeCodeExecutor:
    def __init__(self):
        self.allowed_imports = {
            'math', 'numpy', 'matplotlib', 'plotly', 'd3'
        }
        self.forbidden_patterns = [
            'import os', 'import sys', 'subprocess', 'eval', 'exec',
            '__import__', 'open(', 'file(', 'input(', 'raw_input('
        ]
    
    def validate_code(self, code: str) -> bool:
        """Validate that code is safe to execute"""
        for pattern in self.forbidden_patterns:
            if pattern in code.lower():
                return False
        return True
    
    async def execute_python_safe(self, code: str) -> Dict[str, Any]:
        """Execute Python code in sandboxed environment"""
        if not self.validate_code(code):
            raise ValueError("Code contains forbidden patterns")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Run in restricted environment
            result = subprocess.run([
                'python', '-c', f'''
import sys
import builtins
import math
import numpy as np

# Restrict builtins
builtins.__dict__.clear()
builtins.__dict__.update({{
    'print': print,
    'len': len,
    'range': range,
    'math': math,
    'np': np
}})

exec(open("{temp_file}").read())
                '''
            ], capture_output=True, text=True, timeout=10)
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr
            }
        finally:
            os.unlink(temp_file)