"""ZETTA Prompt Template Engine."""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from core.zetta.utils.errors import ValidationError


@dataclass
class PromptTemplate:
    """Prompt template supporting variable interpolation, composition, and versioning."""

    name: str
    template: str
    system_prompt: str = ""
    version: str = "1.0.0"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def extract_variables(self) -> List[str]:
        """Extract variable placeholders formatted as {variable_name}."""
        return re.findall(r"\{([a-zA-Z0-9_]+)\}", self.template)

    def format(self, **kwargs) -> str:
        """Substitute template variables with provided keyword arguments."""
        missing = [var for var in self.extract_variables() if var not in kwargs]
        if missing:
            raise ValidationError(
                f"Missing required template variables for prompt '{self.name}': {', '.join(missing)}"
            )
        try:
            return self.template.format(**kwargs)
        except Exception as e:
            raise ValidationError(f"Error formatting prompt '{self.name}': {e}")
