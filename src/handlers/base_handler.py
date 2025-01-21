from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseHandler(ABC):
    """Базовый класс для всех обработчиков."""
    
    def __init__(self, required_params=None, optional_params=None):
        self.required_params = required_params or []
        self.optional_params = optional_params or {}
        self.params = {}
    
    def validate_params(self, **kwargs) -> None:
        """Проверяет наличие всех обязательных параметров."""
        missing_params = [param for param in self.required_params if param not in kwargs]
        if missing_params:
            raise ValueError(f"Missing required parameters: {', '.join(missing_params)}")
    
    def prepare_params(self, **kwargs) -> None:
        """Подготавливает параметры, добавляя значения по умолчанию."""
        self.params = {**self.optional_params}
        self.params.update(kwargs)
    
    @abstractmethod
    def process(self) -> Dict[str, Any]:
        """Основная логика обработчика."""
        pass
    
    def __call__(self, **kwargs) -> Dict[str, Any]:
        """Точка входа в обработчик."""
        self.validate_params(**kwargs)
        self.prepare_params(**kwargs)
        return self.process() 