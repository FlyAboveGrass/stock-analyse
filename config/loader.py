import os
import yaml
from pathlib import Path
from typing import Any, Dict
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class ConfigLoader:
    """配置文件加载器"""
    
    @staticmethod
    def load(config_path: str = "config.yaml") -> Dict[str, Any]:
        """
        加载配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            配置字典
        """
        config_file = Path(config_path)
        
        if not config_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 处理环境变量替换
        config = ConfigLoader._process_env_vars(config)
        
        return config
    
    @staticmethod
    def _process_env_vars(config: Any) -> Any:
        """
        递归处理配置中的环境变量
        
        Args:
            config: 配置对象
            
        Returns:
            处理后的配置对象
        """
        if isinstance(config, dict):
            return {k: ConfigLoader._process_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [ConfigLoader._process_env_vars(item) for item in config]
        elif isinstance(config, str):
            # 替换 ${VAR} 格式的环境变量
            if config.startswith('${') and config.endswith('}'):
                var_name = config[2:-1]
                return os.getenv(var_name, config)
            return config
        else:
            return config
