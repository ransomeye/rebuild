# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm/orchestration/prompt_templates/__init__.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Package initialization for prompt templates

def get_template(template_name: str) -> str:
    """
    Get template content by name.
    
    Args:
        template_name: Name of template
        
    Returns:
        Template content as string
    """
    from pathlib import Path
    templates_dir = Path(__file__).parent
    template_path = templates_dir / f"{template_name}.j2"
    
    if template_path.exists():
        return template_path.read_text()
    return ""

