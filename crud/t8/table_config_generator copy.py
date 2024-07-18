import os
import json
from sqlalchemy import inspect, String, Integer, Float, DateTime, Date, Boolean, Enum
from sqlalchemy.orm import class_mapper

def generate_table_config(engine, table_name):
    inspector = inspect(engine)
    columns = inspector.get_columns(table_name)
    
    config_path = f'table_configs/{table_name}_config.json'
    
    # 检查配置文件是否存在
    if os.path.exists(config_path):
        # 读取现有的配置文件
        with open(config_path, 'r') as f:
            config = json.load(f)
            return config
        
    config = {
        "table_name": table_name,
        "columns": []
    }

    for column in columns:
        column_config = {
            "name": column['name'],
            "label": column['name'],
            "type": str(column['type']),
            "nullable": column['nullable'],
            "primary_key": column['primary_key']
        }

        # Determine input type and additional properties
        if isinstance(column['type'], String):
            column_config['input_type'] = 'text'
        elif isinstance(column['type'], (Integer, Float)):
            column_config['input_type'] = 'number'
        elif isinstance(column['type'], (DateTime, Date)):
            column_config['input_type'] = 'date'
        elif isinstance(column['type'], Boolean):
            column_config['input_type'] = 'checkbox'
        elif isinstance(column['type'], Enum):
            column_config['input_type'] = 'select'
            column_config['options'] = column['type'].enums
        else:
            column_config['input_type'] = 'text'

        config['columns'].append(column_config)

    # Save configuration to a JSON file
    with open(f'table_configs/{table_name}_config.json', 'w') as f:
        json.dump(config, f, indent=2)

    return config

# Generate configurations for all tables
def generate_all_table_configs(engine):
    inspector = inspect(engine)
    for table_name in inspector.get_table_names():
        generate_table_config(engine, table_name)

# # Call this function after creating the engine
# generate_all_table_configs(engine)