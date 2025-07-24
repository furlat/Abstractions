"""
Mermaid Rendering Utilities

This module provides utilities for rendering mermaid diagrams quickly during development.
Includes both HTML file generation and optional CLI rendering if mermaid-cli is available.
"""

import os
import tempfile
import webbrowser
from typing import Optional
from pathlib import Path
import subprocess
import sys

def render_mermaid_to_html(mermaid_code: str, title: str = "Entity Visualization", open_browser: bool = True) -> str:
    """
    Render mermaid code to an HTML file for quick viewing.
    
    Args:
        mermaid_code: The mermaid diagram code
        title: Title for the HTML page
        open_browser: Whether to automatically open the browser
        
    Returns:
        Path to the generated HTML file
    """
    
    # Clean up mermaid code - remove markdown code blocks if present
    clean_code = mermaid_code.strip()
    if clean_code.startswith("```mermaid"):
        clean_code = clean_code[10:]  # Remove ```mermaid
    if clean_code.endswith("```"):
        clean_code = clean_code[:-3]  # Remove ```
    clean_code = clean_code.strip()
    
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10.6.1/dist/mermaid.min.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        
        .container {{
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        h1 {{
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }}
        
        .mermaid {{
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 400px;
        }}
        
        .code-section {{
            margin-top: 30px;
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 4px;
            border: 1px solid #e9ecef;
        }}
        
        .code-section h3 {{
            margin-top: 0;
            color: #495057;
        }}
        
        pre {{
            background-color: #f1f3f4;
            padding: 15px;
            border-radius: 4px;
            overflow-x: auto;
            font-family: 'Courier New', monospace;
        }}
        
        .refresh-btn {{
            position: fixed;
            top: 20px;
            right: 20px;
            background-color: #007bff;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }}
        
        .refresh-btn:hover {{
            background-color: #0056b3;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        
        <button class="refresh-btn" onclick="window.location.reload()">Refresh</button>
        
        <div class="mermaid">
{clean_code}
        </div>
        
        <div class="code-section">
            <h3>Mermaid Code</h3>
            <pre><code>{clean_code}</code></pre>
        </div>
    </div>
    
    <script>
        mermaid.initialize({{ 
            startOnLoad: true,
            theme: 'default',
            flowchart: {{
                useMaxWidth: true,
                htmlLabels: true
            }},
            gitGraph: {{
                mainBranchName: 'main',
                showCommitLabel: true,
                showBranches: true
            }}
        }});
    </script>
</body>
</html>"""
    
    # Create temporary HTML file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        f.write(html_content)
        html_path = f.name
    
    print(f"[RENDER] Mermaid diagram rendered to: {html_path}")
    
    if open_browser:
        try:
            webbrowser.open(f"file://{html_path}")
            print("[RENDER] Opened in browser")
        except Exception as e:
            print(f"[WARNING] Could not open browser: {e}")
    
    return html_path

def render_mermaid_to_svg(mermaid_code: str, output_path: Optional[str] = None) -> Optional[str]:
    """
    Render mermaid code to SVG using mermaid-cli if available.
    
    Args:
        mermaid_code: The mermaid diagram code
        output_path: Path for output SVG file (optional)
        
    Returns:
        Path to the generated SVG file or None if mermaid-cli not available
    """
    try:
        # Check if mermaid-cli is available
        subprocess.run(['mmdc', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("[WARNING] mermaid-cli not found. Install with: npm install -g @mermaid-js/mermaid-cli")
        return None
    
    # Clean up mermaid code
    clean_code = mermaid_code.strip()
    if clean_code.startswith("```mermaid"):
        clean_code = clean_code[10:]
    if clean_code.endswith("```"):
        clean_code = clean_code[:-3]
    clean_code = clean_code.strip()
    
    # Create temporary input file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.mmd', delete=False) as f:
        f.write(clean_code)
        input_path = f.name
    
    try:
        # Determine output path
        if output_path is None:
            output_path = tempfile.mktemp(suffix='.svg')
        
        # Run mermaid-cli
        subprocess.run([
            'mmdc', 
            '-i', input_path,
            '-o', output_path,
            '--theme', 'default',
            '--width', '1200',
            '--height', '800'
        ], check=True)
        
        print(f"[RENDER] SVG diagram generated: {output_path}")
        return output_path
        
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Error generating SVG: {e}")
        return None
    finally:
        # Clean up temporary input file
        os.unlink(input_path)

def quick_render(mermaid_code: str, title: str = "Entity Visualization", format: str = "html") -> Optional[str]:
    """
    Quick render function for development iteration.
    
    Args:
        mermaid_code: The mermaid diagram code
        title: Title for the visualization
        format: Output format ('html' or 'svg')
        
    Returns:
        Path to the generated file
    """
    if format.lower() == 'html':
        return render_mermaid_to_html(mermaid_code, title)
    elif format.lower() == 'svg':
        return render_mermaid_to_svg(mermaid_code)
    else:
        print(f"[ERROR] Unsupported format: {format}. Use 'html' or 'svg'")
        return None

def print_mermaid_code(mermaid_code: str, title: str = "Mermaid Diagram") -> None:
    """
    Print mermaid code with nice formatting for terminal output.
    
    Args:
        mermaid_code: The mermaid diagram code
        title: Title for the output
    """
    print(f"\n{'='*60}")
    print(f"[MERMAID] {title}")
    print('='*60)
    print(mermaid_code)
    print('='*60)

# Example usage and testing
if __name__ == "__main__":
    # Test with a simple mermaid diagram
    test_diagram = """
    graph TD
        A[Student Alice] --> B[Assessment]
        A --> C[Recommendation]
        B -.-> C
        
        classDef student fill:#e1f5fe,stroke:#01579b,stroke-width:2px
        classDef assessment fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
        classDef recommendation fill:#e8f5e8,stroke:#388e3c,stroke-width:2px
        
        class A student
        class B assessment
        class C recommendation
    """
    
    print("[TEST] Testing mermaid rendering utilities...")
    
    # Test HTML rendering
    html_path = render_mermaid_to_html(test_diagram, "Test Entity Visualization")
    
    # Test SVG rendering (if mermaid-cli is available)
    svg_path = render_mermaid_to_svg(test_diagram)
    
    # Test print function
    print_mermaid_code(test_diagram, "Test Diagram")
    
    print("\n[TEST] Testing complete!")