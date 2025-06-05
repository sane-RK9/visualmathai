import asyncio
import hashlib
from pathlib import Path
from typing import Optional
from manim import *
class ManimRenderer:
    def __init__(self, output_dir: str = "runtime/cache/manim"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def render_scene(self, scene_code: str, scene_name: str = "DynamicScene") -> str:
        # Generate unique filename
        scene_hash = hashlib.md5(scene_code.encode()).hexdigest()
        output_file = self.output_dir / f"{scene_name}_{scene_hash}.mp4"
        
        if output_file.exists():
            return str(output_file)
        
        # Create temporary Python file
        temp_file = self.output_dir / f"temp_{scene_hash}.py"
        
        full_scene_code = f"""
from manim import *

{scene_code}
        """
        
        temp_file.write_text(full_scene_code)
        
        # Run Manim
        cmd = [
            "manim", str(temp_file), scene_name,
            "-o", str(output_file),
            "--write_to_movie"
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"Manim render failed: {stderr.decode()}")
        
        # Clean up temp file
        temp_file.unlink()
        
        return str(output_file)